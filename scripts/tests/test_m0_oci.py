"""OCI trust boundaries and unknown results; no Docker, network or listeners."""
import base64
import copy
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_registry as registry
import m0_oci as oci
import m0_oci_client as cli
import m0_oauth as oauth
from m0_response_loss import ResponseLoss


def response(data=b'', status=200, headers=None):
    return status, oauth.BinaryBody(data, headers or {}), None, registry.ORIGIN + '/v2/'


class RegistryBoundaries(unittest.TestCase):
    def test_contract_rejects_scope_expansion_changed_origin_and_unpinned_client(self):
        original = registry.contract()
        for change in [lambda v:v['pat_profiles']['write'].append('all'),
                       lambda v:v.update(origin='https://example.test'),
                       lambda v:v['client'].update(sha256='0'*64)]:
            value=copy.deepcopy(original);change(value)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'profile.json';path.write_text(json.dumps(value))
                with patch.object(registry,'PROFILE',path), self.assertRaises(ValueError):registry.contract()

    def test_challenge_never_follows_foreign_realm_or_service(self):
        client=Mock()
        valid='Bearer realm="'+registry.ORIGIN+'/v2/token",service="container_registry",scope="*"'
        client.request.return_value=response(status=401,headers={'WWW-Authenticate':valid})
        self.assertEqual(registry.challenge(client)['service'],'container_registry')
        for value in [valid.replace(registry.ORIGIN,'https://example.test'),valid.replace('container_registry','other'), 'Basic realm="fixture"']:
            client.request.return_value=response(status=401,headers={'WWW-Authenticate':value})
            with self.subTest(value=value), self.assertRaises(RuntimeError):registry.challenge(client)
        self.assertTrue(all(v.args[0]=='GET' and v.args[1]=='/v2/' for v in client.request.call_args_list))

    def test_upload_location_cannot_change_image_origin_or_smuggle_a_query_token(self):
        valid='/v2/'+registry.IMAGE+'/blobs/uploads/fixture-123'
        self.assertEqual(registry.location(valid),valid)
        for value in ['https://example.test'+valid,valid+'?token=synthetic',valid.replace(registry.ORG,'other'),valid+'#fragment']:
            with self.subTest(value=value), self.assertRaises(RuntimeError):registry.location(value)

    def test_token_metadata_is_not_claimed_as_a_local_signature_check(self):
        pat={'user':'alice','value':'synthetic','scopes':['read:package']}
        claims={'UserID':7,'Scope':'read:package','nbf':1,'exp':86401}
        def token(value):
            part=base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
            return 'synthetic.'+part+'.synthetic'
        client=Mock();client.request.return_value=response(json.dumps({'token':token(claims)}).encode())
        _,meta=registry.mint(client,pat)
        self.assertFalse(meta['claims_locally_signature_verified'])
        self.assertEqual(meta['declared_lifetime_seconds'],86400)
        claims['Scope']='all';client.request.return_value=response(json.dumps({'token':token(claims)}).encode())
        with self.assertRaises(RuntimeError):registry.mint(client,pat)

    def test_image_fixture_descriptors_match_exact_layer_and_config_bytes(self):
        config,layer,manifest=registry.fixture('a'*40,'m0-one')
        row=json.loads(manifest)
        self.assertEqual(row['config']['digest'],registry.sha(config))
        self.assertEqual(row['layers'][0]['digest'],registry.sha(layer))
        raw=gzip.decompress(layer)
        self.assertEqual(json.loads(config)['rootfs']['diff_ids'],[registry.sha(raw)])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertEqual(archive.extractfile('m0-source.txt').read(),registry.SOURCE_BYTES)
        self.assertNotEqual(manifest,registry.fixture('a'*40,'m0-two')[2])

    def test_manifest_digest_uses_received_bytes_instead_of_json_reencoding(self):
        raw=b'{ "schemaVersion": 2 }\n';digest=registry.sha(raw)
        client=Mock();client.request.return_value=response(raw,headers={'Content-Type':registry.OCI_MANIFEST,'Docker-Content-Digest':digest})
        self.assertEqual(registry.read_manifest(client,'synthetic',digest)[0],digest)
        client.request.return_value=response(raw+b' ',headers={'Content-Type':registry.OCI_MANIFEST,'Docker-Content-Digest':digest})
        with self.assertRaises(RuntimeError):registry.read_manifest(client,'synthetic',digest)

    def test_bad_blob_digest_or_bytes_never_become_success(self):
        digest=registry.sha(b'expected');client=Mock()
        client.request.return_value=response(b'wrong',headers={'Docker-Content-Digest':digest})
        with self.assertRaises(RuntimeError):registry.read_blob(client,'synthetic',digest)
        client.request.reset_mock()
        with self.assertRaises(ValueError):registry.read_blob(client,'synthetic','m0-tag')
        client.request.assert_not_called()

    def test_unapproved_or_header_injection_input_stops_before_io(self):
        client=object.__new__(oauth.Client);client.base=registry.ORIGIN;client.opener=Mock()
        for headers in [{'Authorization':'synthetic'},{'Accept':'a\r\nb'},{'Content-Range':3}]:
            with self.subTest(headers=headers), self.assertRaises(ValueError):client.request('GET','/v2/',headers=headers)
        client.opener.open.assert_not_called()


class UnknownWrites(unittest.TestCase):
    def test_missing_old_digest_is_a_gap_and_permission_fixture_is_read_separately(self):
        source='a'*40
        _,_,original=registry.fixture(source,'m0-retention-original')
        _,_,moved=registry.fixture(source,'m0-moved-tag')
        _,_,main=registry.fixture(source,'m0-main');main_digest=registry.sha(main)
        client=Mock();client.request.return_value=response(status=404);record=Mock()
        with patch.object(oci,'put_manifest',side_effect=[registry.sha(original),registry.sha(moved)]), \
             patch.object(oci,'read_manifest',side_effect=[(registry.sha(moved),{},moved),(main_digest,{},main)]) as reads:
            oci.tag_changes(client,'synthetic',source,main,main_digest,record)
        self.assertEqual(record.call_args.args[1],'gap')
        self.assertEqual(reads.call_args_list[-1].args[2],main_digest)
        self.assertNotIn('latest',str(client.request.call_args_list))

    def test_upload_start_timeout_without_location_does_not_guess_or_start_another(self):
        client=Mock();client.request.return_value=response(status=404);record=Mock()
        with patch.object(oci,'fault',return_value={'upstream_status':202,'automatic_retries':0}):
            oci.fault_start(client,'synthetic',True,record)
        self.assertEqual(record.call_args.kwargs['reconciliation']['state'],'unknown')
        self.assertTrue(all(v.args[0]=='HEAD' for v in client.request.call_args_list))

    def test_complete_blob_timeout_is_observed_only_after_exact_digest_read(self):
        data=b'M0 exact complete blob '+b'x'*512;digest=registry.sha(data)
        client=Mock();client.request.side_effect=[response(status=202),response(status=200),
            response(data,headers={'Docker-Content-Digest':digest}),response(status=404)]
        record=Mock()
        with patch.object(oci,'start_upload',return_value='/v2/'+registry.IMAGE+'/blobs/uploads/fixture'), \
             patch.object(oci,'fault',return_value={'upstream_status':201,'automatic_retries':0}), \
             patch.object(oci.secrets,'token_bytes',return_value=b'x'*512):
            client.request.side_effect=[response(status=200),response(data,headers={'Docker-Content-Digest':digest}),response(status=404)]
            oci.fault_commit(client,'synthetic',True,record)
        self.assertEqual(record.call_args.kwargs['reconciliation']['state'],'observed')
        self.assertTrue(all(v.args[0] in ('GET','HEAD') for v in client.request.call_args_list))

    def test_partial_blob_with_zero_complete_objects_stays_unknown(self):
        client=Mock();client.request.side_effect=[response(status=404),response(status=204),response(status=204)]
        record=Mock();path='/v2/'+registry.IMAGE+'/blobs/uploads/fixture'
        with patch.object(oci,'start_upload',return_value=path),patch.object(oci,'fault',return_value={'upstream_status':None,'automatic_retries':0}):
            oci.fault_commit(client,'synthetic',True,record,partial=True)
        self.assertEqual(record.call_args.kwargs['reconciliation']['state'],'unknown')
        self.assertFalse(any(v.args[0] in ('POST','PUT','PATCH') for v in client.request.call_args_list))

    def test_fault_capability_cannot_target_another_namespace_or_partial_manifest(self):
        for op,path,data,partial in [('oci_start','/v2/other/image/blobs/uploads/',b'',None),
            ('oci_manifest','/v2/'+registry.IMAGE+'/manifests/m0-tag',b'{}',1),
            ('oci_blob_commit','/v2/'+registry.IMAGE+'/blobs/uploads/fixture?token=synthetic',b'x',None)]:
            with self.subTest(op=op),self.assertRaises(ValueError):ResponseLoss(op,path,'synthetic',data,forward=True,partial_bytes=partial)
        value=ResponseLoss('oci_start','/v2/'+registry.IMAGE+'/blobs/uploads/','synthetic',b'',forward=True)
        self.assertEqual(value.method,'POST')


class ClientIsolation(unittest.TestCase):
    def test_client_configuration_disables_docker_credentials_and_keeps_tls_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'ca.crt').write_text('synthetic task CA')
            with patch.object(cli,'RUNTIME',root),patch.dict(cli.os.environ,{'DOCKER_AUTH_CONFIG':'synthetic-private'}):
                env=cli.client_env({'user':'alice','value':'synthetic-private'})
            self.assertNotIn('DOCKER_AUTH_CONFIG',env)
            data=json.loads((root/'regctl.json').read_text())
            self.assertFalse(data['incDockerCred']);self.assertFalse(data['incDockerCert'])
            self.assertEqual(data['hosts']['localhost:18443']['tls'],'enabled')
            self.assertEqual(Path(env['REGCTL_CONFIG']).parent,root)

    def test_unpinned_client_binary_cannot_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'regctl';path.write_bytes(b'synthetic')
            with self.assertRaises(ValueError):cli.client_path(path)


if __name__ == '__main__':
    unittest.main()
