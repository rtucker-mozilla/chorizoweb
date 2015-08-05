"""empty message

Revision ID: 28ded70f2f95
Revises: 1e0485123a2b
Create Date: 2015-05-12 08:03:01.358734

"""

# revision identifiers, used by Alembic.
revision = '28ded70f2f95'
down_revision = '1e0485123a2b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('system_pings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('system_id', sa.Integer(), nullable=True),
    sa.Column('ping_hash', sa.String(length=80), nullable=False),
    sa.Column('ping_time', sa.DateTime(), nullable=True),
    sa.Column('pong_time', sa.DateTime(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['system_id'], ['systems.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ping_hash')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('system_pings')
    ### end Alembic commands ###