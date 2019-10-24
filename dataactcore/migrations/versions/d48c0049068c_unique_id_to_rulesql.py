""" Unique ID to ruleSQL

Revision ID: d48c0049068c
Revises: d753553fa79b
Create Date: 2019-10-24 13:40:08.217910

"""

# revision identifiers, used by Alembic.
revision = 'd48c0049068c'
down_revision = 'd753553fa79b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_data_broker():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rule_sql', sa.Column('unique_id', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade_data_broker():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('rule_sql', 'unique_id')
    # ### end Alembic commands ###

