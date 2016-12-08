from collections import namedtuple, OrderedDict
import itertools

import iso3166

from dataactcore.interfaces.db import GlobalDB
from dataactcore.models.fsrs import (
    FSRSGrant, FSRSProcurement, FSRSSubcontract, FSRSSubgrant)
from dataactcore.models.stagingModels import AwardFinancial


def _country_name(code):
    """Convert a country code to the country name; return None if invalid"""
    country = iso3166.countries.get(code, None)
    if country:
        return country.name


def _zipcode_guard(model, field_prefix, match_usa):
    """Get the zip code or not depending on country value"""
    is_usa = getattr(model, field_prefix + '_country') == 'USA'
    zipcode = getattr(model, field_prefix + '_zip')
    if (match_usa and is_usa) or (not match_usa and not is_usa):
        return zipcode


class CopyValues():
    """Copy a field value from one of our existing models"""
    def __init__(self, subcontract=None, subgrant=None, procurement=None,
                 grant=None, award=None):
        self.procurement_field = procurement
        self.subcontract_field = subcontract
        self.grant_field = grant
        self.subgrant_field = subgrant
        self.award_field = award

    def transform(self, models):
        if self.subcontract_field and models.subcontract:
            return getattr(models.subcontract, self.subcontract_field)
        elif self.subgrant_field and models.subgrant:
            return getattr(models.subgrant, self.subgrant_field)
        elif self.procurement_field and models.procurement:
            return getattr(models.procurement, self.procurement_field)
        elif self.grant_field and models.grant:
            return getattr(models.grant, self.grant_field)
        elif self.award_field and models.award:
            return getattr(models.award, self.award_field)


def copy_subaward_field(field_name):
    return CopyValues(field_name, field_name)


def copy_prime_field(field_name):
    return CopyValues(procurement=field_name, grant=field_name)


def todo():
    return CopyValues()         # noop


class SubawardLogic():
    """Perform custom logic relating to the subaward (i.e. subcontract or
    subgrant). Instantiated with two functions: one for subcontracts, one for
    subawards"""
    def __init__(self, subcontract_fn, subgrant_fn):
        self.subcontract_fn = subcontract_fn
        self.subgrant_fn = subgrant_fn

    def transform(self, models):
        if models.subcontract:
            return self.subcontract_fn(models.subcontract)
        elif models.subgrant:
            return self.subgrant_fn(models.subgrant)


mappings = OrderedDict([
    ('SubAwardeeOrRecipientLegalEntityName',
        CopyValues('company_name', 'awardee_name')),
    ('SubAwardeeOrRecipientUniqueIdentifier', copy_subaward_field('duns')),
    ('SubAwardeeUltimateParentUniqueIdentifier',
        copy_subaward_field('parent_duns')),
    ('SubAwardeeUltimateParentLegalEntityName',
        CopyValues(subcontract='parent_company_name')),
    ('LegalEntityAddressLine1',
        CopyValues('company_address_street', 'awardee_address_street')),
    ('LegalEntityCityName',
        CopyValues('company_address_city', 'awardee_address_city')),
    ('LegalEntityStateCode',
        CopyValues('company_address_state', 'awardee_address_state')),
    ('LegalEntityZIP+4', SubawardLogic(
        lambda subcontract:
            _zipcode_guard(subcontract, 'company_address', True),
        lambda subgrant: _zipcode_guard(subgrant, 'awardee_address', True)
    )),
    ('LegalEntityForeignPostalCode', SubawardLogic(
        lambda subcontract:
            _zipcode_guard(subcontract, 'company_address', False),
        lambda subgrant: _zipcode_guard(subgrant, 'awardee_address', False)
    )),
    ('LegalEntityCongressionalDistrict',
        CopyValues('company_address_district', 'awardee_address_district')),
    ('LegalEntityCountryCode',
        CopyValues('company_address_country', 'awardee_address_country')),
    ('LegalEntityCountryName', SubawardLogic(
        lambda subcontract: _country_name(subcontract.company_address_country),
        lambda subgrant: _country_name(subgrant.awardee_address_country)
    )),
    ('HighCompOfficer1FullName', copy_subaward_field('top_paid_fullname_1')),
    ('HighCompOfficer1Amount', copy_subaward_field('top_paid_amount_1')),
    ('HighCompOfficer2FullName', copy_subaward_field('top_paid_fullname_2')),
    ('HighCompOfficer2Amount', copy_subaward_field('top_paid_amount_2')),
    ('HighCompOfficer3FullName', copy_subaward_field('top_paid_fullname_3')),
    ('HighCompOfficer3Amount', copy_subaward_field('top_paid_amount_3')),
    ('HighCompOfficer4FullName', copy_subaward_field('top_paid_fullname_4')),
    ('HighCompOfficer4Amount', copy_subaward_field('top_paid_amount_4')),
    ('HighCompOfficer5FullName', copy_subaward_field('top_paid_fullname_5')),
    ('HighCompOfficer5Amount', copy_subaward_field('top_paid_amount_5')),
    ('SubcontractAwardAmount', CopyValues(subcontract='subcontract_amount')),
    ('TotalFundingAmount', CopyValues(subgrant='subaward_amount')),
    ('NAICS', CopyValues(subcontract='naics')),
    ('NAICS_Description', todo()),
    ('CFDA_NumberAndTitle', CopyValues(subgrant='cfda_numbers')),
    ('AwardingSubTierAgencyName', copy_subaward_field('funding_agency_name')),
    ('AwardingSubTierAgencyCode', copy_subaward_field('funding_agency_id')),
    ('AwardDescription',
        CopyValues('overall_description', 'project_description')),
    ('ActionDate',
        CopyValues(subcontract='subcontract_date', grant='obligation_date')),
    ('PrimaryPlaceOfPerformanceCityName',
        copy_subaward_field('principle_place_city')),
    ('PrimaryPlaceOfPerformanceAddressLine1',
        copy_subaward_field('principle_place_street')),
    ('PrimaryPlaceOfPerformanceStateCode',
        copy_subaward_field('principle_place_state')),
    ('PrimaryPlaceOfPerformanceZIP+4',
        copy_subaward_field('principle_place_zip')),
    ('PrimaryPlaceOfPerformanceCongressionalDistrict',
        copy_subaward_field('principle_place_district')),
    ('PrimaryPlaceOfPerformanceCountryCode',
        copy_subaward_field('principle_place_country')),
    ('PrimaryPlaceOfPerformanceCountryName', SubawardLogic(
        lambda subcontract: _country_name(subcontract.principle_place_country),
        lambda subgrant: _country_name(subgrant.principle_place_country)
    )),
    ('Vendor Doing As Business Name', copy_subaward_field('dba_name')),
    ('PrimeAwardReportID',
        CopyValues(procurement='contract_number', grant='fain')),
    ('ParentAwardId', CopyValues(procurement='idv_reference_number')),
    ('AwardReportMonth', copy_prime_field('report_period_mon')),
    ('AwardReportYear', copy_prime_field('report_period_year')),
    ('RecModelQuestion1', CopyValues('recovery_model_q1', 'compensation_q1')),
    ('RecModelQuestion2', CopyValues('recovery_model_q2', 'compensation_q2')),
    ('SubawardNumber', CopyValues('subcontract_num', 'subaward_num')),
    ('SubawardeeBusinessType', CopyValues(subcontract='bus_types')),
    ('AwardeeOrRecipientUniqueIdentifier', copy_prime_field('duns'))
])


# Collect the models associated with a single F CSV row
ModelRow = namedtuple(
    'ModelRow', ['award', 'procurement', 'subcontract', 'grant', 'subgrant'])


def submission_procurements(submission_id):
    """Fetch procurements and subcontracts"""
    triplets = GlobalDB.db().session.\
        query(AwardFinancial, FSRSProcurement, FSRSSubcontract).\
        filter(AwardFinancial.submission_id == submission_id).\
        filter(FSRSProcurement.contract_number == AwardFinancial.piid).\
        filter(FSRSSubcontract.parent_id == FSRSProcurement.id)
    for award, proc, sub in triplets:
        yield ModelRow(award, proc, sub, None, None)


def submission_grants(submission_id):
    """Fetch grants and subgrants"""
    triplets = GlobalDB.db().session.\
        query(AwardFinancial, FSRSGrant, FSRSSubgrant).\
        filter(AwardFinancial.submission_id == submission_id).\
        filter(FSRSGrant.fain == AwardFinancial.fain).\
        filter(FSRSSubgrant.parent_id == FSRSGrant.id)
    for award, grant, sub in triplets:
        yield ModelRow(award, None, None, grant, sub)


def generate_f_rows(submission_id):
    """Generated OrderedDicts representing File F rows. Subawards are filtered
    to those relevant to a particular submissionId"""
    for model_row in itertools.chain(submission_procurements(submission_id),
                                     submission_grants(submission_id)):
        result = OrderedDict()
        for key, mapper in mappings.items():
            result[key] = mapper.transform(model_row) or ''
        yield result
