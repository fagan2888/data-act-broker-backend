"""create cgac lookup table

Revision ID: d376eff9557a
Revises: 1a886e694fca
Create Date: 2016-04-12 15:32:14.079379

"""

# revision identifiers, used by Alembic.
revision = 'd376eff9557a'
down_revision = '1a886e694fca'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cgac_lookup',
    sa.Column('cgac_id', sa.Integer(), nullable=False),
    sa.Column('agency_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('cgac_id'),
    sa.UniqueConstraint('agency_id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('cgac_lookup')
    ### end Alembic commands ###
