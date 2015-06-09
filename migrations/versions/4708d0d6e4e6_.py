"""empty message

Revision ID: 4708d0d6e4e6
Revises: 2bd467af2597
Create Date: 2015-06-09 06:36:05.149937

"""

# revision identifiers, used by Alembic.
revision = '4708d0d6e4e6'
down_revision = '2bd467af2597'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('update_group', sa.Column('cronfile', sa.String(length=80), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('update_group', 'cronfile')
    ### end Alembic commands ###
