# -*- coding: utf-8 -*-
"""
Seintinel2A processing commands
"""
import os
import requests
import zipfile
import magic
from urllib.request import urlopen
from urllib.parse import urlsplit
from .exceptions import AsyncProcessError
from .process_object import Process

__license__ = "GPLv3"
__author__ = "Sören Gebbert"
__copyright__ = "Copyright 2016, Sören Gebbert"
__maintainer__ = "Sören Gebbert"
__email__ = "soerengebbert@googlemail.com"

# Mimetypes supported for download
SUPPORTED_MIMETYPES = ["application/zip", "image/tiff", "application/gml", "text/xml",
                       "application/xml", "text/plain", "text/x-python"]
# Suffixes supported in zip files
SUPPORTED_SUFFIXES = [".tif", ".tiff", ".xml", ".gml", ".shp", ".dbf", ".shx", ".atx", ".sbx",
                      ".qix", ".aih", ".prj", ".cpg", ".json"]


class GeoDataDownloadImportSupport(object):
    """
    """

    def __init__(self, config, temp_file_path, download_cache,
                 send_resource_update, message_logger, url_list):
        """ A collection of functions to generate Landsat4-8 scene related import and processing
        commands. Each function returns a process chain that can be executed
        by the async processing classes.

        Args:
            config: The Actinia Core configuration object
            temp_file_path: The path to the temporary directory to store temporary files.
                            It is assumed that this path is available when the generated
                            commands are executed.
            download_cache (str): The path to the download cache
            send_resource_update: The function to call for resource updates
            message_logger: The message logger to be used
            url_list: A list of urls that should be accessed to download imported geodata

        """
        self.config = config
        self.temp_file_path = temp_file_path
        self.user_download_cache_path = download_cache
        self.send_resource_update = send_resource_update
        self.message_logger = message_logger
        self.url_list = url_list
        self.detected_mime_types = []
        self.file_list = []
        self.copy_file_list = []
        self.import_file_info = []

    def _setup(self):
        """Setup the download cache.

        Check the download cache if the file already exists, to avoid redundant downloads.
        Create the cahce if it does not exist and switch into the temporary directory.
        """

        # Create the download cache directory if it does not exists
        if os.path.exists(self.config.DOWNLOAD_CACHE):
            pass
        else:
            os.mkdir(self.config.DOWNLOAD_CACHE)

        # Create the user specific download cache directory to put the downloaded files into it
        if os.path.exists(self.user_download_cache_path):
            pass
        else:
            os.mkdir(self.user_download_cache_path)

        # Change working directory to tempfile directory
        os.chdir(self.temp_file_path)

    def _check_urls(self):
        """Check the urls for access and supported mimetypes.
        If all files are already in the download cache, then
        nothing needs to be downloaded and checked.
        """
        for url in self.url_list:
            # Send a resource update
            if self.send_resource_update is not None:
                self.send_resource_update(message="Checking access to URL: %s" % url)

            # Check if thr URL exists by investigating the HTTP header
            resp = requests.head(url)
            if self.message_logger: self.message_logger.info("%i %s %s" % (resp.status_code,
                                                                           resp.text, resp.headers))

            if resp.status_code != 200:
                raise AsyncProcessError("The URL <%s> can not be accessed." % url)

            # Download 256 bytes from the url and check its mimetype
            response = urlopen(url)
            mime_type = magic.from_buffer(response.read(256), mime=True).lower()
            if self.message_logger: self.message_logger.info(mime_type)

            if mime_type not in SUPPORTED_MIMETYPES:
                raise AsyncProcessError("Mimetype <%s> of url <%s> is not supported. "
                                        "Supported mimetypes are: %s" % (mime_type,
                                                                         url, ",".join(SUPPORTED_MIMETYPES)))

            self.detected_mime_types.append(mime_type)

    def get_download_process_list(self):
        """Create the process list to download, import and preprocess
        geodata location on a remote location

        The downloaded files will be stored in a temporary directory. After the download of all files
        completes, the downloaded files will be moved to the download cache. This avoids broken
        files in case a download was interrupted or stopped by termination.

        This method creates wget calls and mv calls.

        Returns:
            (download_commands, import_file_info)
        """
        self._setup()
        self._check_urls()

        download_commands = []
        count = 0
        create_copy_list = False

        if not self.copy_file_list:
            create_copy_list = True

        # Create the download commands and update process chain
        for url in self.url_list:
            # Extract file name from url and create temp and cache path
            # if the copy_file_path list is empty
            if create_copy_list is True:
                purl = urlsplit(url)
                file_name = os.path.basename(purl.path)
                source = os.path.join(self.temp_file_path, file_name)
                dest = os.path.join(self.user_download_cache_path, file_name)
                self.copy_file_list.append((source, dest))
            else:
                source, dest = self.copy_file_list[count]

            # Download file only if it does not exist in the download cache
            if os.path.isfile(dest) is False:

                wget = "/usr/bin/wget"
                wget_params = list()
                wget_params.append("-t5")
                wget_params.append("-c")
                wget_params.append("-q")
                wget_params.append("-O")
                wget_params.append("%s" % source)
                wget_params.append(url)

                p = Process(exec_type="exec", executable=wget, executable_params=wget_params,
                            skip_permission_check=True)

                download_commands.append(p)
                if source != dest:
                    copy = "/bin/mv"
                    copy_params = list()
                    copy_params.append(source)
                    copy_params.append(dest)

                    p = Process(exec_type="exec", executable=copy, executable_params=copy_params,
                                skip_permission_check=True)
                    download_commands.append(p)
            count += 1

        # Create the import file info list
        self.import_file_info = []

        for mtype, (source, dest) in zip(self.detected_mime_types, self.copy_file_list):
            self.import_file_info.append((mtype, source, dest))

        return download_commands, self.import_file_info

    @staticmethod
    def get_file_rename_command(file_path, file_name):
        """Generate the file-rename process list so that the input file has a specific
        file name that is accessible in the process chain via file_id

        Args:
            file_path:
            file_name:

        Returns:
            Process

        """
        p = Process(exec_type="exec", executable="/bin/mv",
                    executable_params=[file_path, file_name],
                    skip_permission_check=True)
        return p

    @staticmethod
    def get_raster_import_command(file_path, raster_name):
        """Generate raster import process list that makes use of r.import

        Args:
            file_path:
            raster_name:

        Returns:
            Process

        """
        p = Process(exec_type="grass",
                    executable="r.import",
                    executable_params=["input=%s" % file_path,
                                       "output=%s" % raster_name,
                                       "--q"],
                    skip_permission_check=True)

        return p

    @staticmethod
    def get_vector_import_command(input_source, vector_name, layer_name=None):
        """Generate raster import process list that makes use of v.import

        Args:
            input_source (str): The input source can be a file path or a database string
            vector_name (str): The name of the new vector layer
            layer_name (str): The layer name or comma separated list of layer names
                              that should be imported from the input source

        Returns:
            Process

        """
        if layer_name is not None:
            exec_params = ["input=%s" % input_source,
                           "output=%s" % vector_name,
                           "layer=%s" % layer_name,
                           "--q"]
        else:
            exec_params = ["input=%s" % input_source,
                           "output=%s" % vector_name,
                           "--q"]

        p = Process(exec_type="grass",
                    executable="v.import",
                    executable_params=exec_params,
                    skip_permission_check=True)
        return p

    def perform_file_validation(self, filepath, mimetype=None):
        """Perform a file validation check of mimetypes and zip bombs.
        This function checks zip files and returns the file names of the extracted file(s).
        If mimetype is None all supported mimetypes will be checked.

        Args:
            filepath (str): The path to a file that should be checked against supported mimetypes and
                      zip-bomb security.
            mimetype (str): A specific mimetype that should be checked

        Returns:
            (list)
            file_list A list of files that will be in the current working directory
        """
        file_name = os.path.basename(filepath)
        file_list = [file_name]

        if not os.path.isfile(filepath):
            raise AsyncProcessError("File <%s> does not exist." % filepath)

        mime_type = magic.from_file(filepath, mime=True)
        if self.message_logger: self.message_logger.info(mime_type)

        if mime_type not in SUPPORTED_MIMETYPES:
            raise AsyncProcessError("Mimetype of url <%s> is not supported. "
                                    "Supported mimetypes are: %s" % (filepath, ",".join(SUPPORTED_MIMETYPES)))

        if mime_type.lower() == "application/zip":
            z = zipfile.ZipFile(filepath)
            total_sum = sum(e.file_size for e in z.infolist())
            compressed_sum = sum(e.compress_size for e in z.infolist())
            compression_ratio = total_sum / compressed_sum

            print(compressed_sum, total_sum, compression_ratio)

            if compression_ratio > 10000:
                raise AsyncProcessError("Compression ratio is larger than 10000.")

            if total_sum > 2 ** 32:
                raise AsyncProcessError("Files larger than 4GB are not supported in zip files.")

            for name in z.namelist():
                file_name, suffix = os.path.splitext(name)
                file_list.append(file_name)
                if suffix not in SUPPORTED_SUFFIXES:
                    raise AsyncProcessError("Suffix %s of zipped file <%s> is not supported. "
                                            "Supported suffixes in zip files are: %s" % (suffix, name,
                                                                                         ",".join(SUPPORTED_SUFFIXES)))
            z.close()

        return file_list
