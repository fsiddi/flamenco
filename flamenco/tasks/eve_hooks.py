# -*- encoding: utf-8 -*-

import logging

import werkzeug.exceptions as wz_exceptions
from pillar.api.utils.authorization import user_matches_roles

from flamenco import current_flamenco, ROLES_REQUIRED_TO_VIEW_ITEMS, ROLES_REQUIRED_TO_VIEW_LOGS

log = logging.getLogger(__name__)


def check_task_permission_fetch(task_doc):

    if current_flamenco.current_user_is_flamenco_admin():
        return

    if not current_flamenco.manager_manager.user_is_manager():
        # Subscribers can read Flamenco tasks.
        if user_matches_roles(ROLES_REQUIRED_TO_VIEW_ITEMS):
            return
        raise wz_exceptions.Forbidden()

    if not current_flamenco.manager_manager.user_manages(mngr_doc_id=task_doc.get('manager')):
        # FIXME: Regular user or not task-owning manager, undefined behaviour as of yet.
        # # Run validation process, since GET on nodes entry point is public
        # check_permissions('flamenco_tasks', task_doc, 'GET',
        #                   append_allowed_methods=True)
        raise wz_exceptions.Forbidden()

    # Managers can re-fetch their own tasks to validate their local task cache.


def check_task_log_permission_fetch(task_log_docs):
    if user_matches_roles(ROLES_REQUIRED_TO_VIEW_LOGS):
        return
    raise wz_exceptions.Forbidden()


def task_logs_remove_fields(task_log_docs):
    """Some fields are added by Eve, but we don't need those for task logs."""

    for task_log in task_log_docs.get('_items', []):
        task_log_remove_fields(task_log)


def task_log_remove_fields(task_log):
    task_log.pop('_etag', None)
    task_log.pop('_updated', None)
    task_log.pop('_created', None)


def check_task_permission_fetch_resource(response):
    if current_flamenco.current_user_is_flamenco_admin():
        return

    if not current_flamenco.manager_manager.user_is_manager():
        # Subscribers can read Flamenco tasks.
        if user_matches_roles(ROLES_REQUIRED_TO_VIEW_ITEMS):
            return

    raise wz_exceptions.Forbidden()


def check_task_permissions_create_delete(task_doc, original_doc=None):
    """For now, only admins are allowed to create and delete tasks."""

    if not current_flamenco.current_user_is_flamenco_admin():
        raise wz_exceptions.Forbidden()

    # FIXME: check user access to the project.


def check_task_permissions_edit(task_doc, original_doc=None):
    """For now, only admins and owning managers are allowed to edit."""

    if not current_flamenco.current_user_is_flamenco_admin():
        raise wz_exceptions.Forbidden()

    # FIXME: check user access to the project.


def update_job_status(task_doc, original_doc):
    """Update the job status given the new task status."""

    current_status = task_doc.get('status')
    old_status = original_doc.get('status')

    if current_status == old_status:
        return

    task_id = task_doc['_id']
    job_id = task_doc.get('job')
    if not job_id:
        log.warning('update_job_status(): Task %s has no job, this should not happen.', task_id)
        return

    current_flamenco.job_manager.update_job_after_task_status_change(
        job_id, task_id, current_status)


def setup_app(app):
    app.on_fetched_resource_flamenco_task_logs += check_task_log_permission_fetch
    app.on_fetched_resource_flamenco_task_logs += task_logs_remove_fields
    app.on_fetched_item_flamenco_task_logs += task_log_remove_fields

    app.on_fetched_item_flamenco_tasks += check_task_permission_fetch
    app.on_fetched_resource_flamenco_tasks += check_task_permission_fetch_resource

    app.on_insert_flamenco_tasks += check_task_permissions_create_delete
    app.on_delete_flamenco_tasks += check_task_permissions_create_delete
    app.on_update_flamenco_tasks += check_task_permissions_edit
    app.on_replace_flamenco_tasks += check_task_permissions_edit
    app.on_replaced_flamenco_tasks += update_job_status