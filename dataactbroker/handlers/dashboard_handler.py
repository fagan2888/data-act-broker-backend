import logging

from flask import g

from dataactcore.utils.jsonResponse import JsonResponse
from dataactcore.utils.responseException import ResponseException
from dataactcore.interfaces.db import GlobalDB
from sqlalchemy import or_, case

from dataactcore.utils.statusCode import StatusCode
from dataactcore.models.lookups import PUBLISH_STATUS_DICT

from datetime import datetime
from dataactbroker.helpers.generic_helper import fy
from dataactcore.models.userModel import User
from dataactcore.models.jobModels import Submission
from dataactcore.models.domainModels import CGAC, FREC


logger = logging.getLogger(__name__)

FILE_TYPES = ['A', 'B', 'C', 'cross-AB', 'cross-BC', 'cross-CD1', 'cross-CD2']


def validate_historic_dashboard_filters(filters, graphs=False):
    """ Validate historic dashboard filters

        Args:
            filters: dictionary representing the filters provided to the historic dashboard endpoints
            graphs: whether or not to validate the files and rules as well

        Exceptions:
            ResponseException if filter is invalid
    """
    required_filters = ['quarters','fys','agencies']
    if graphs:
        required_filters.extend(['files', 'rules'])
    missing_filters = [required_filter for required_filter in required_filters if required_filter not in filters]
    if missing_filters:
        raise ResponseException('The following filters were not provided: {}'.format(','.join(missing_filters)))

    wrong_filter_types = [key for key, value in filters.items() if not isinstance(value, list)]
    if wrong_filter_types:
        raise ResponseException('The following filters were not lists: {}'.format(','.join(wrong_filter_types)))

    for quarter in filters['quarters']:
        if quarter not in range(1,5):
            raise ResponseException('Quarters must be a list of integers, each ranging 1-4, or an empty list.')

    current_fy = fy(datetime.now())
    for fiscal_year in filters['fys']:
        if fiscal_year not in range(2017,current_fy+1):
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
    if not g.user.website_admin:
        affiliation_filters = []
        cgac_codes = [aff.cgac.cgac_code for aff in g.user.affiliations if aff.cgac]
        frec_codes = [aff.frec.frec_code for aff in g.user.affiliations if aff.frec]

        affiliation_filters.append(Submission.user_id == g.user.user_id)

        if cgac_codes:
            affiliation_filters.append(Submission.cgac_code.in_(cgac_codes))
        if frec_codes:
            affiliation_filters.append(Submission.frec_code.in_(frec_codes))

        query = query.filter(or_(*affiliation_filters))

    if filters['quarters']:
        periods = [quarter * 3 for quarter in filters['quarters']]
        query = query.filter(Submission.reporting_fiscal_period.in_(periods))

    if filters['fys']:
        query = query.filter(Submission.reporting_fiscal_year.in_(filters['fys']))
    
    if filters['agencies']:
        agency_filters = []
        cgac_codes = [cgac_code for cgac_code in filters['agencies'] if len(cgac_code) == 3]
        frec_codes = [frec_code for frec_code in filters['agencies'] if len(frec_code) == 4]
        
        if len(cgac_codes) + len(frec_codes) != len(filters['agencies']):
            raise ResponseException('All codes in the agencies filter must be valid agency codes',
                                    StatusCode.CLIENT_ERROR)
        # If the number of CGACs or FRECs returned from a query using the codes doesn't match the length of
        # each list (ignoring duplicates) then something included wasn't a valid agency
        cgac_list = set(cgac_codes)
        frec_list = set(frec_codes)
        if (cgac_list and sess.query(CGAC).filter(CGAC.cgac_code.in_(cgac_list)).count() != len(cgac_list)) or \
                (frec_list and sess.query(FREC).filter(FREC.frec_code.in_(frec_list)).count() != len(frec_list)):
            raise ResponseException("All codes in the agencies filter must be valid agency codes",
                                    StatusCode.CLIENT_ERROR)
        if cgac_list:
            agency_filters.append(Submission.cgac_code.in_(cgac_list))
        if frec_list:
            agency_filters.append(Submission.frec_code.in_(frec_list))

        query = query.filter(or_(*agency_filters))

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
