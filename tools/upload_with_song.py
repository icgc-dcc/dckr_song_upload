#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from overture_song.model import ApiConfig, Manifest, ManifestEntry, SongError
from overture_song.client import Api, ManifestClient, StudyClient
from overture_song.tools import FileUploadClient
from overture_song.utils import setup_output_file_path
import subprocess
import requests


def create_manifest(api, analysis_id, payload_file, manifest_file,files_dir):
    payload = json.load(open(payload_file))

    with open(os.path.join(files_dir,manifest_file), 'w') as outfile:
        outfile.write(analysis_id+'\t\t\n')
        for i in range(0,len(payload.get('file'))):
            file_object = payload.get('file')[i]
            outfile.write(retrieve_object_id(api,analysis_id,
                                             file_object.get('fileName'),
                                             file_object.get('fileMd5sum'))+'\t'+os.path.join(files_dir,file_object.get('fileName'))+'\t'+file_object.get('fileMd5sum')+'\n')
    return

def retrieve_object_id(api, analysis_id, file_name, file_md5sum):
    analysis = api.get_analysis(analysis_id).__dict__
    for file in analysis.get('file'):
        if file.__dict__.get('fileName') == file_name and file.__dict__.get('fileMd5sum') == file_md5sum:
            return file.__dict__.get('objectId')
    raise Exception('The object id could not be found for '+file_name)


def upload_payload(api, payload_file):
    api_upload = api.upload(json.load(open(payload_file)))
    upload_status = api.status(api_upload.uploadId)

    if not upload_status.state == 'VALIDATED':
        raise Exception("Song upload could not be validated - Analysis id "+upload_status.analysisId+", Current State: "+upload_status.state)
    return upload_status

def validate_payload_against_analysis(api,analysis_id, payload_file):
    json_data = json.load(open(payload_file))
    payload_files = []
    for file in json_data.get('file'):
        payload_files.append(file)

    for file in api.get_analysis_files(analysis_id):
        tmp_file = {'fileName':file.fileName,'fileSize':file.fileSize,'fileType':file.fileType,'fileMd5sum':file.fileMd5sum,'fileAccess':file.fileAccess}
        if not tmp_file in payload_files:
            raise Exception("The payload to be uploaded and the analysis on SONG do not match.")
    return True

def main():
    parser = argparse.ArgumentParser(description='Upload a payload using SONG')
    parser.add_argument('-s', '--study-id', dest="study_id", help="Study ID", required=True)
    parser.add_argument('-u', '--server-url', dest="server_url", help="Server URL", required=True)
    parser.add_argument('-p', '--payload', dest="payload", help="JSON Payload", required=True)
    parser.add_argument('-o', '--output', dest="output", help="Output manifest file", required=True)
    parser.add_argument('-d', '--input-dir', dest="input_dir", help="Payload files directory", required=True)
    parser.add_argument('-t', '--access-token', dest="access_token", default=os.environ.get('ACCESSTOKEN',None),help="Server URL")
    parser.add_argument('-j','--json',dest="json_output")
    results = parser.parse_args()

    study_id = results.study_id
    server_url = results.server_url
    access_token = results.access_token
    payload_file = results.payload
    analysis_id = json.load(open(payload_file)).get('analysisId')


    api_config = ApiConfig(server_url,study_id,access_token)
    api = Api(api_config)

    upload_status = upload_payload(api,payload_file)
    try:
        api.save(upload_status.uploadId, ignore_analysis_id_collisions=True)
    except Exception as e:
        song_error = json.loads(str(e))
        if song_error.get('errorId') != "duplicate.analysis.attempt":
            raise e

    if api.get_analysis(analysis_id).__dict__['analysisState'] == "PUBLISHED":
        validate_payload_against_analysis(api, analysis_id, payload_file)

    manifest_filename = results.output
    create_manifest(api,analysis_id,payload_file,manifest_filename,results.input_dir)

    if not api.get_analysis(analysis_id).__dict__['analysisState'] == "PUBLISHED":
        subprocess.check_output(['score-client','upload','--manifest',os.path.join(results.input_dir,manifest_filename), '--force'])

    response = requests.put(server_url+'/studies/'+study_id+'/analysis/publish/'+analysis_id, headers={'Authorization':'Bearer '+access_token})
    if response.status_code > 300:
        raise Exception(response.text)

    if not api.get_analysis(analysis_id).__dict__['analysisState'] == "PUBLISHED":
        raise Exception("The analysis %s has not been published correctly." % analysis_id)

    if results.json_output:
        with open(os.path.join(results.input_dir,manifest_filename),'r') as f:
            manifest_json = {}
            manifest_json['analysis_id'] = f.readline().split('\t')[0]
            manifest_json['files'] = []
            for line in f.readlines():
                _file = {}
                _file['object_id'] = line.split('\t')[0]
                _file['file_name'] = line.split('\t')[1]
                _file['md5'] = line.split('\t')[2].strip('\n')
                manifest_json['files'].append(_file)
            with open(os.path.join(results.input_dir,results.json_output),'w') as outfile:
                json.dump(manifest_json, outfile)

if __name__ == "__main__":
    main()
