"""Adding principle place street to subaward

Revision ID: 4be5e411246b
Revises: 87d7a9b0ea7b
Create Date: 2019-08-07 15:13:50.092991

"""

# revision identifiers, used by Alembic.
revision = '4be5e411246b'
down_revision = '87d7a9b0ea7b'
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
    op.add_column('subaward', sa.Column('place_of_perform_street', sa.Text(), nullable=True))
    op.add_column('subaward', sa.Column('sub_place_of_perform_street', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade_data_broker():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('subaward', 'sub_place_of_perform_street')
    op.drop_column('subaward', 'place_of_perform_street')
    # ### end Alembic commands ###

