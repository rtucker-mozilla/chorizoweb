"""empty message

Revision ID: 4b189495dccd
Revises: 56994cff016a
Create Date: 2014-09-02 09:29:06.804353

"""

# revision identifiers, used by Alembic.
revision = '4b189495dccd'
down_revision = '56994cff016a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('system_backup_logs', sa.Column('stderr', sa.Text(), nullable=True))
    op.add_column('system_backup_logs', sa.Column('stdout', sa.Text(), nullable=True))
    op.drop_column('system_backups', 'stderr')
    op.drop_column('system_backups', 'stdout')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('system_backups', sa.Column('stdout', mysql.TEXT(), nullable=True))
    op.add_column('system_backups', sa.Column('stderr', mysql.TEXT(), nullable=True))
    op.drop_column('system_backup_logs', 'stdout')
    op.drop_column('system_backup_logs', 'stderr')
    ### end Alembic commands ###