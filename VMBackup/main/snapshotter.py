#!/usr/bin/env python
#
# VM Backup extension
#
# Copyright 2014 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import urlparse
import httplib
import traceback
import datetime
import multiprocessing as mp
from common import CommonVariables
from HttpUtil import HttpUtil

class SnapshotError(object):
    def __init__(self):
        self.errorcode = CommonVariables.success
        self.sasuri = None
    def __str__(self):
        return 'errorcode: ' + str(self.errorcode) + ' sasuri: ' + str(self.sasuri)

class SnapshotResult(object):
    def __init__(self):
        self.errors = []

    def __str__(self):
        error_str = ""
        for error in self.errors:
            error_str+=(str(error)) + "\n"
        return error_str

class Snapshotter(object):
    """description of class"""
    def __init__(self, logger):
        self.logger = logger

    def snapshot(self, sasuri, meta_data,snapshot_result_error,global_logger,global_error_logger):
        result = None
        temp_logger=''
        error_logger=''
        snapshot_error = SnapshotError()
        if(sasuri is None):
            error_logger = error_logger + " Failed to do the snapshot because sasuri is none "
            snapshot_error.errorcode = CommonVariables.error
            snapshot_error.sasuri = sasuri
        try:
            sasuri_obj = urlparse.urlparse(sasuri)
            if(sasuri_obj is None or sasuri_obj.hostname is None):
                error_logger = error_logger + " Failed to parse the sasuri "
                snapshot_error.errorcode = CommonVariables.error
                snapshot_error.sasuri = sasuri
            else:
                start_time = datetime.datetime.utcnow()
                body_content = ''
                headers = {}
                headers["Content-Length"] = '0'
                if(meta_data is not None):
                    for meta in meta_data:
                        key = meta['Key']
                        value = meta['Value']
                        headers["x-ms-meta-" + key] = value
                self.logger.log(str(headers))
                http_util = HttpUtil(self.logger)
                sasuri_obj = urlparse.urlparse(sasuri + '&comp=snapshot')
                temp_logger = temp_logger + 'start calling the snapshot rest api. '
                
                result = CommonVariables.error_http_failure
                resp = http_util.HttpCall('PUT',sasuri_obj, body_content, headers = headers)
                
                if(resp != None):
                    self.logger.log("snapshot resp-header: " + str(resp.getheaders()))
                    temp_logger = temp_logger + "snapshot resp-header: " + str(resp.getheaders())
                    self.logger.log("snapshot resp status: " + str(resp.status))
                    temp_logger = temp_logger + "snapshot resp status: " + str(resp.status)
                    responseBody = resp.read()
                    if(responseBody is not None):
                        self.logger.log("snapshot responseBody: " + (responseBody).decode('utf-8-sig'))
                        temp_logger = temp_logger + "snapshot responseBody: " + (responseBody).decode('utf-8-sig')

                    if(resp.status == 200 or resp.status == 201):
                        result = CommonVariables.success
                    else:
                        result = resp.status
                else:
                    self.logger.log("snapshot Http connection response is None")
                    temp_logger = temp_logger + "snapshot Http connection response is None"

                temp_logger = temp_logger + ' snapshot api returned: {0} '.format(result)
                end_time = datetime.datetime.utcnow()
                time_taken=end_time-start_time
                temp_logger = temp_logger + ' time taken for snapshot ' + str(time_taken)
                if(result != CommonVariables.success):
                    snapshot_error.errorcode = result
                    snapshot_error.sasuri = sasuri
        except Exception as e:
            errorMsg = " Failed to do the snapshot with error: %s, stack trace: %s" % (str(e), traceback.format_exc())
            error_logger = error_logger + errorMsg
            snapshot_error.errorcode = CommonVariables.error
            snapshot_error.sasuri = sasuri
        temp_logger=temp_logger + ' snapshot ends..'
        global_logger.put(temp_logger)
        global_error_logger.put(error_logger)
        snapshot_result_error.put(snapshot_error)

    def snapshot_seq(self, sasuri, meta_data):
        result = None
        snapshot_error = SnapshotError()
        if(sasuri is None):
            self.logger.log("Failed to do the snapshot because sasuri is none",False,'Error')
            snapshot_error.errorcode = CommonVariables.error
            snapshot_error.sasuri = sasuri
        try:
            sasuri_obj = urlparse.urlparse(sasuri)
            if(sasuri_obj is None or sasuri_obj.hostname is None):
                self.logger.log("Failed to parse the sasuri",False,'Error')
                snapshot_error.errorcode = CommonVariables.error
                snapshot_error.sasuri = sasuri
            else:
                body_content = ''
                headers = {}
                headers["Content-Length"] = '0'
                if(meta_data is not None):
                    for meta in meta_data:
                        key = meta['Key']
                        value = meta['Value']
                        headers["x-ms-meta-" + key] = value
                self.logger.log(str(headers))
                http_util = HttpUtil(self.logger)
                sasuri_obj = urlparse.urlparse(sasuri + '&comp=snapshot')
                self.logger.log("start calling the snapshot rest api")
                result = http_util.Call('PUT',sasuri_obj, body_content, headers = headers)
                self.logger.log("snapshot api returned: {0}".format(result))
                if(result != CommonVariables.success):
                    snapshot_error.errorcode = result
                    snapshot_error.sasuri = sasuri
        except Exception as e:
            errorMsg = "Failed to do the snapshot with error: %s, stack trace: %s" % (str(e), traceback.format_exc())
            self.logger.log(errorMsg, False, 'Error')
            snapshot_error.errorcode = CommonVariables.error
            snapshot_error.sasuri = sasuri
        return snapshot_error


    def snapshotall(self, paras):
        self.logger.log("doing snapshotall now...")
        snapshot_result = SnapshotResult()
        try:
            mp_jobs = []
            global_logger = mp.Queue() 
            global_error_logger = mp.Queue()
            snapshot_result_error = mp.Queue()
            blobs = paras.blobs
            if blobs is not None:
                mp_jobs = [mp.Process(target=self.snapshot,args=(blob, paras.backup_metadata,snapshot_result_error,global_logger,global_error_logger)) for blob in blobs]
                for job in mp_jobs:
                    job.start()
                for job in mp_jobs:
                    job.join()
                    self.logger.log('end of snapshot process')
                logging = [global_logger.get() for job in mp_jobs]
                self.logger.log(str(logging))
                error_logging = [global_error_logger.get() for job in mp_jobs]
                self.logger.log(error_logging,False,'Error')
                if not snapshot_result_error.empty(): 
                    results = [snapshot_result_error.get() for job in mp_jobs]
                    for result in results:
                        if(result.errorcode != CommonVariables.success):
                            snapshot_result.errors.append(result)
                return snapshot_result
            else:
                self.logger.log("the blobs are None")
                return snapshot_result
        except Exception as e:
            self.logger.log("Do sequential snapshoting")
            blobs = paras.blobs
            if blobs is not None:
                for blob in blobs:
                    snapshotError = self.snapshot_seq(blob, paras.backup_metadata)
                    if(snapshotError.errorcode != CommonVariables.success):
                        snapshot_result.errors.append(snapshotError)
                return snapshot_result
            else:
                self.logger.log("the blobs are None")
                return snapshot_result
