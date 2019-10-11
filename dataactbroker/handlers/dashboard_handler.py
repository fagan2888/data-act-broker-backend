import logging

from datetime import datetime
from sqlalchemy import or_, and_, case

from dataactcore.interfaces.db import GlobalDB
from dataactcore.models.domainModels import CGAC, FREC
from dataactcore.models.jobModels import Submission
from dataactcore.models.lookups import PUBLISH_STATUS_DICT, RULE_SEVERITY_DICT, FILE_TYPE_DICT_LETTER_ID
from dataactcore.models.userModel import User
from dataactcore.models.validationModels import RuleSql

from dataactcore.utils.jsonResponse import JsonResponse
from dataactcore.utils.responseException import ResponseException
from dataactcore.utils.statusCode import StatusCode

from dataactbroker.helpers.generic_helper import fy
from dataactbroker.helpers.filters_helper import permissions_filter, agency_filter


logger = logging.getLogger(__name__)

FILE_TYPES = ['A', 'B', 'C', 'cross-AB', 'cross-BC', 'cross-CD1', 'cross-CD2']


def list_rule_labels(files, error_level='warning', fabs=False):
    """ Returns a list of rule labels based on the files and error type provided

        Args:
            files: A list of files for which to return rule labels. If blank, return all matching other arguments
            error_level: A string indicating whether to return errors, warnings, or both. Defaults to warning
            fabs: A boolean indicating whether to return FABS or DABS rules. Defaults to False

        Returns:
            JsonResponse of the rule labels the arguments indicate. JsonResponse error if invalid file types are
            provided or any file types are provided for FABS
    """
    # Make sure list is empty when requesting FABS rules
    if fabs and len(files) > 0:
        return JsonResponse.error(ValueError('Files list must be empty for FABS rules'), StatusCode.CLIENT_ERROR)

    invalid_files = [invalid_file for invalid_file in files if invalid_file not in FILE_TYPES]
    if invalid_files:
        return JsonResponse.error(ValueError('The following are not valid file types: {}'.
                                             format(', '.join(invalid_files))),
                                  StatusCode.CLIENT_ERROR)

    sess = GlobalDB.db().session

    rule_label_query = sess.query(RuleSql.rule_label)

    # If the error level isn't "mixed" add a filter on which severity to pull
    if error_level == 'error':
        rule_label_query = rule_label_query.filter_by(rule_severity_id=RULE_SEVERITY_DICT['fatal'])
    elif error_level == 'warning':
        rule_label_query = rule_label_query.filter_by(rule_severity_id=RULE_SEVERITY_DICT['warning'])

    # If specific files have been specified, add a filter to get them
    if files:
        file_type_filters = []
        for file in files:
            if file in ['A', 'B', 'C']:
                file_type_filters.append(and_(RuleSql.file_id == FILE_TYPE_DICT_LETTER_ID[file],
                                              RuleSql.target_file_id.is_(None)))
            else:
                file_types = file.split('-')[1]
                # Append both orders of the source/target files to the list
                file_type_filters.append(and_(RuleSql.file_id == FILE_TYPE_DICT_LETTER_ID[file_types[:1]],
                                              RuleSql.target_file_id == FILE_TYPE_DICT_LETTER_ID[file_types[1:]]))
                file_type_filters.append(and_(RuleSql.file_id == FILE_TYPE_DICT_LETTER_ID[file_types[1:]],
                                              RuleSql.target_file_id == FILE_TYPE_DICT_LETTER_ID[file_types[:1]]))
        rule_label_query = rule_label_query.filter(or_(*file_type_filters))
    elif not fabs:
        # If not the rules are not FABS, exclude FABS rules
        rule_label_query = rule_label_query.filter(RuleSql.file_id != FILE_TYPE_DICT_LETTER_ID['FABS'])
    else:
        # If the rule is FABS, add a filter to only get FABS rules
        rule_label_query = rule_label_query.filter_by(file_id=FILE_TYPE_DICT_LETTER_ID['FABS'])

    return JsonResponse.create(StatusCode.OK, {'labels': [label.rule_label for label in rule_label_query.all()]})


def validate_historic_dashboard_filters(filters, graphs=False):
    """ Validate historic dashboard filters

        Args:
            filters: dictionary representing the filters provided to the historic dashboard endpoints
            graphs: whether or not to validate the files and rules as well

        Exceptions:
            ResponseException if filter is invalid
    """
    required_filters = ['quarters', 'fys', 'agencies']
    if graphs:
        required_filters.extend(['files', 'rules'])
    missing_filters = [required_filter for required_filter in required_filters if required_filter not in filters]
    if missing_filters:
        raise ResponseException('The following filters were not provided: {}'.format(','.join(missing_filters)))

    wrong_filter_types = [key for key, value in filters.items() if not isinstance(value, list)]
    if wrong_filter_types:
        raise ResponseException('The following filters were not lists: {}'.format(','.join(wrong_filter_types)))

    for quarter in filters['quarters']:
        if quarter not in range(1, 5):
            raise ResponseException('Quarters must be a list of integers, each ranging 1-4, or an empty list.')

    current_fy = fy(datetime.now())
    for fiscal_year in filters['fys']:
        if fiscal_year not in range(2017, current_fy + 1):
            raise ResponseException('Fiscal Years must be a list of integers, each ranging from 2017 through the'
                                    ' current fiscal year, or an empty list.')

    for agency in filters['agencies']:
        if not isinstance(agency, str):
            raise ResponseException('Agencies must be a list of strings, or an empty list.')

    if graphs:
        for file_type in filters['files']:
            if file_type not in FILE_TYPES:
                raise ResponseException('Files must be a list of one or more of the following, or an empty list: {}'.
                                        format(','.join(FILE_TYPES)))

        for rule in filters['rules']:
            if not isinstance(rule, str):
                raise ResponseException('Rules must be a list of strings, or an empty list.')


def apply_historic_dabs_filters(sess, query, filters, graphs=False):
    """ Apply the filters provided to the query provided

        Args:
            sess: the database connection
            query: the baseline sqlalchemy query to work from
            filters: dictionary representing the filters provided to the historic dashboard endpoints
            graphs: whether or not to apply the files and rules filters as well

        Exceptions:
            ResponseException if filter is invalid
    """

    # Applying general user permissions standard for all the filters
    query = permissions_filter(query)

    if filters['quarters']:
        periods = [quarter * 3 for quarter in filters['quarters']]
        query = query.filter(Submission.reporting_fiscal_period.in_(periods))

    if filters['fys']:
        query = query.filter(Submission.reporting_fiscal_year.in_(filters['fys']))

    if filters['agencies']:
        query = agency_filter(sess, query, Submission, Submission, filters['agencies'])

    if graphs:
        # TODO: For the graphs endpoint
        pass
        # for file_type in filters['files']:
        #     query = query.filter()
        # for rule in filters['rules']:
        #     query = query.filter()

    return query


def historic_dabs_warning_summary(filters):
    """ Generate a list of submission summaries appropriate on the filters provided

        Args:
            filters: dictionary representing the filters provided to the historic dashboard endpoints

        Return:
            JsonResponse of the submission summaries appropriate on the filters provided
    """
    sess = GlobalDB.db().session

    validate_historic_dashboard_filters(filters, graphs=False)

    summary_query = sess.query(
        Submission.submission_id,
        (Submission.reporting_fiscal_period / 3).label('quarter'),
        Submission.reporting_fiscal_year.label('fy'),
        User.name.label('certifier'),
        case([
            (FREC.frec_code.isnot(None), FREC.frec_code),
            (CGAC.cgac_code.isnot(None), CGAC.cgac_code)
        ]).label('agency_code'),
        case([
            (FREC.agency_name.isnot(None), FREC.agency_name),
            (CGAC.agency_name.isnot(None), CGAC.agency_name)
        ]).label('agency_name')
    ).join(User, User.user_id == Submission.certifying_user_id).\
        outerjoin(CGAC, CGAC.cgac_code == Submission.cgac_code).\
        outerjoin(FREC, FREC.frec_code == Submission.frec_code).\
        filter(Submission.publish_status_id.in_([PUBLISH_STATUS_DICT['published'], PUBLISH_STATUS_DICT['updated']])).\
        filter(Submission.d2_submission.is_(False))

    summary_query = apply_historic_dabs_filters(sess, summary_query, filters, graphs=False)

    results = []
    for query_result in summary_query.all():
        result_dict = {
            'submission_id': query_result.submission_id,
            'fy': query_result.fy,
            'quarter': query_result.quarter,
            'agency': {
                'name': query_result.agency_name,
                'code': query_result.agency_code,
            },
            'certifier': query_result.certifier
        }
        results.append(result_dict)

    return JsonResponse.create(StatusCode.OK, results)