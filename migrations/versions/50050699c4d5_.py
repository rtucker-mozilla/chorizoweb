"""empty message

Revision ID: 50050699c4d5
Revises: 3e24919ec2eb
Create Date: 2015-05-20 09:22:26.832622

"""

# revision identifiers, used by Alembic.
revision = '50050699c4d5'
down_revision = '3e24919ec2eb'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('system_pongs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('system_id', sa.Integer(), nullable=True),
    sa.Column('pong_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['system_id'], ['systems.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_column(u'scripts_installed', 'system_id')
    op.drop_column(u'system_pings', 'pong_time')
    op.drop_column(u'system_pings', 'success')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(u'system_pings', sa.Column('success', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False))
    op.add_column(u'system_pings', sa.Column('pong_time', mysql.DATETIME(), nullable=True))
    op.add_column(u'scripts_installed', sa.Column('system_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.drop_table('system_pongs')
    ### end Alembic commands ###
