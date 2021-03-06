# -*- coding: utf-8 -*-
"""Running a custom UNIX process outside the GRASS GIS environment
"""
import pickle
from flask import jsonify, make_response

from .ephemeral_processing import EphemeralProcessing
from .resource_base import ResourceBase
from .common.redis_interface import enqueue_job
from .common.exceptions import AsyncProcessError
from .user_auth import check_location_mapset_module_access
from .common.process_object import Process

__license__ = "GPLv3"
__author__     = "Sören Gebbert"
__copyright__  = "Copyright 2016, Sören Gebbert"
__maintainer__ = "Sören Gebbert"
__email__      = "soerengebbert@googlemail.com"


class AsyncEphemeralCustomResource(ResourceBase):
    """This class represents a custom process resource
    that will be asynchronously executed without the initialization
    of the GRASS environment.
    """
    def __init__(self):
        ResourceBase.__init__(self)

    def post(self, executable):
        """Run a custom process

        The process is identified by executable

        Args:
            executable (str): Name of the executable

        Process arguments must be provided as JSON document in the POST request::

            ["arg_1", "arg_2", "arg_3", "arg_4", ...]

        Returns:
            flask.Response:
            The HTTP status and a JSON document that includes the
            status URL of the export task that must be polled for updates.

        """
        # Preprocess the post call
        rdc = self.preprocess(has_json=True)

        if rdc:
            rdc.set_user_data(executable)
            enqueue_job(self.job_timeout, start_job, rdc)

        html_code, response_model = pickle.loads(self.response_data)
        return make_response(jsonify(response_model), html_code)


def start_job(*args):
    processing = EphemeralCustomProcessing(*args)
    processing.run()


class EphemeralCustomProcessing(EphemeralProcessing):
    """Run a custom process asynchronously
    """
    def __init__(self, *args):
        """Setup the variables of this class

        Args:
            rdc (ResourceDataContainer): The data container that contains all required variables for processing
        """

        EphemeralProcessing.__init__(self, *args)
        self.executable = self.rdc.user_data
        self.executable_params = self.rdc.request_data

        self._update_num_of_steps(1)

    def _execute(self, skip_permission_check=False):
        """Overwrite this function in subclasses

        Setup the user credentials, check the executable access and run the process
        """
        # Setup the user credentials and logger
        self._setup(init_grass=False)

        # Check if the user has access to the required process executable
        resp = check_location_mapset_module_access(self.user_credentials,
                                                   self.config,
                                                   module_name=self.executable)

        if resp is not None:
            raise AsyncProcessError("Executable <%s> is not suported"%self.executable)

        p = Process(exec_type="exec",
                         executable=self.executable,
                         executable_params=self.executable_params,
                         stdin_source=None)

        self._run_process(p)


    def _final_cleanup(self):
        """Final cleanup called in the run function at the very end of processing
        """
        # Nothing to cleanup
        pass
