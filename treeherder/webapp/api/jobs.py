# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated

from treeherder.webapp.api.utils import (UrlQueryFilter, with_jobs,
                                         oauth_required, get_option)


class JobsViewSet(viewsets.ViewSet):
    """
    This viewset is responsible for the jobs endpoint.

    """
    throttle_scope = 'jobs'

    @with_jobs
    def retrieve(self, request, project, jm, pk=None):
        """
        GET method implementation for detail view

        Return a single job with log_references and
        artifact names and links to the artifact blobs.
        """
        obj = jm.get_job(pk)
        if obj:
            job = obj[0]
            job["resource_uri"] = reverse("jobs-detail",
                kwargs={"project": jm.project, "pk": job["id"]})
            job["logs"] = jm.get_log_references(pk)

            # make artifact ids into uris
            artifact_refs = jm.get_job_artifact_references(pk)
            job["artifacts"] = []
            for art in artifact_refs:
                ref = reverse("artifact-detail",
                              kwargs={"project": jm.project, "pk": art["id"]})
                art["resource_uri"] = ref
                job["artifacts"].append(art)

            option_collections = jm.refdata_model.get_all_option_collections()
            job["platform_option"] = get_option(job, option_collections)

            return Response(job)
        else:
            return Response("No job with id: {0}".format(pk), 404)

    @with_jobs
    def list(self, request, project, jm):
        """
        GET method implementation for list view

        """
        filter = UrlQueryFilter(request.QUERY_PARAMS)

        offset = filter.pop("offset", 0)
        count = min(int(filter.pop("count", 10)), 1000)

        full = filter.pop('full', 'true').lower() == 'true'
        objs = jm.get_job_list(offset, count, full, filter.conditions)

        if objs:
            option_collections = jm.refdata_model.get_all_option_collections()
            for job in objs:
                job["platform_option"] = get_option(job, option_collections)

        return Response(objs)

    @action(permission_classes=[IsAuthenticated])
    @with_jobs
    def update_state(self, request, project, jm, pk=None):
        """
        Change the state of a job.
        """
        state = request.DATA.get('state', None)

        # check that this state is valid
        if state not in jm.STATES:
            return Response(
                {"message": ("'{0}' is not a valid state.  Must be "
                             "one of: {1}".format(
                                 state,
                                 ", ".join(jm.STATES)
                             ))},
                status=400,
            )

        if not pk:  # pragma nocover
            return Response({"message": "job id required"}, status=400)

        obj = jm.get_job(pk)
        if obj:
            jm.set_state(pk, state)
            return Response({"message": "state updated to '{0}'".format(state)})
        else:
            return Response("No job with id: {0}".format(pk), 404)

    @action(permission_classes=[IsAuthenticated])
    @with_jobs
    def cancel(self, request, project, jm, pk=None):
        """
        Change the state of a job.
        """

        obj = jm.get_job(pk)
        if obj:
            jm.cancel_job(obj[0]['job_guid'])
            return Response({"message": "canceled job '{0}'".format(obj[0]['job_guid'])})
        else:
            return Response("No job with id: {0}".format(pk), 404)

    @with_jobs
    @oauth_required
    def create(self, request, project, jm):
        """
        This method adds a job to a given resultset.
        The incoming data has the same structure as for
        the objectstore ingestion.
        """
        jm.load_job_data(request.DATA)

        return Response({'message': 'Job successfully updated'})

