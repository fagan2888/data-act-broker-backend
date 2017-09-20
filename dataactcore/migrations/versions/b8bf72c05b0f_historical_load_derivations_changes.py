"""Historical Load Derivations Changes

Revision ID: b8bf72c05b0f
Revises: 1fc4844837cf
Create Date: 2017-09-18 13:01:50.097333

"""

# revision identifiers, used by Alembic.
revision = 'b8bf72c05b0f'
down_revision = '1fc4844837cf'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_data_broker():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('fpds_contracting_offices',
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('FPDS_contracting_office_id', sa.Integer(), nullable=False),
    sa.Column('department_id', sa.Text(), nullable=True),
    sa.Column('department_name', sa.Text(), nullable=True),
    sa.Column('agency_code', sa.Text(), nullable=True),
    sa.Column('agency_name', sa.Text(), nullable=True),
    sa.Column('contracting_office_code', sa.Text(), nullable=True),
    sa.Column('contracting_office_name', sa.Text(), nullable=True),
    sa.Column('start_date', sa.DateTime(), nullable=True),
    sa.Column('end_date', sa.DateTime(), nullable=True),
    sa.Column('address_city', sa.Text(), nullable=True),
    sa.Column('address_state', sa.Text(), nullable=True),
    sa.Column('zip_code', sa.Text(), nullable=True),
    sa.Column('country_code', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('FPDS_contracting_office_id')
    )
    op.create_index(op.f('ix_fpds_contracting_offices_agency_code'), 'fpds_contracting_offices', ['agency_code'], unique=False)
    op.create_index(op.f('ix_fpds_contracting_offices_contracting_office_code'), 'fpds_contracting_offices', ['contracting_office_code'], unique=False)
    op.create_index(op.f('ix_fpds_contracting_offices_department_id'), 'fpds_contracting_offices', ['department_id'], unique=False)
    op.add_column('published_award_financial_assistance', sa.Column('awarding_office_name', sa.Text(), nullable=True))
    op.add_column('published_award_financial_assistance', sa.Column('funding_office_name', sa.Text(), nullable=True))
    op.add_column('published_award_financial_assistance', sa.Column('legal_entity_city_code', sa.Text(), nullable=True))
    op.add_column('published_award_financial_assistance', sa.Column('legal_entity_foreign_descr', sa.Text(), nullable=True))
    op.add_column('states', sa.Column('fips_code', sa.Text(), nullable=True))
    ### end Alembic commands ###


def downgrade_data_broker():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('states', 'fips_code')
    op.drop_column('published_award_financial_assistance', 'legal_entity_foreign_descr')
    op.drop_column('published_award_financial_assistance', 'legal_entity_city_code')
    op.drop_column('published_award_financial_assistance', 'funding_office_name')
    op.drop_column('published_award_financial_assistance', 'awarding_office_name')
    op.drop_index(op.f('ix_fpds_contracting_offices_department_id'), table_name='fpds_contracting_offices')
    op.drop_index(op.f('ix_fpds_contracting_offices_contracting_office_code'), table_name='fpds_contracting_offices')
    op.drop_index(op.f('ix_fpds_contracting_offices_agency_code'), table_name='fpds_contracting_offices')
    op.drop_table('fpds_contracting_offices')
    ### end Alembic commands ###
