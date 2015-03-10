"""Add child_task to Workers

Revision ID: 4ab0a557a2ea
Revises: bb419a4193b
Create Date: 2015-03-09 18:04:31.602352

"""

# revision identifiers, used by Alembic.
revision = '4ab0a557a2ea'
down_revision = 'bb419a4193b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('worker', schema=None) as batch_op:
        batch_op.add_column(sa.Column('child_task', sa.String(length=20), nullable=True))

    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('worker', schema=None) as batch_op:
        batch_op.drop_column('child_task')

    ### end Alembic commands ###