# Copyright (C) 2014  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import yaml

import obnamlib


class DumpRepositoryPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.add_subcommand(
            'dump-repo', self.cmd_dump_repo, arg_synopsis='')

        self.app.settings.boolean(
            ['dump-repo-file-metadata'],
            'dump metadata about files?')

    def cmd_dump_repo(self, args):
        repo = self.app.get_repository_object()
        yaml.safe_dump_all(
            self.dump_repository(repo),
            stream=self.app.output,
            default_flow_style=False)
        repo.close()

    def dump_repository(self, repo):
        yield self.dump_client_list(repo)
        yield self.dump_chunk_ids(repo)
        for client_name in repo.get_client_names():
            for x in self.dump_client(repo, client_name):
                yield x

    def dump_client_list(self, repo):
        return {
            'client-list': list(repo.get_client_names()),
            }

    def dump_chunk_ids(self, repo):
        return {
            'chunk-ids': list(repo.get_chunk_ids()),
            }

    def dump_client(self, repo, client_name):
        yield {
            'client-name': client_name,
            'encryption-key': repo.get_client_encryption_key_id(client_name),
            'client-keys': self.dump_client_keys(repo, client_name),
            }

        for gen_id in repo.get_client_generation_ids(client_name):
            yield self.dump_generation(repo, client_name, gen_id)

    def dump_client_keys(self, repo, client_name):
        return dict(
            (obnamlib.repo_key_name(key),
             repo.get_client_key(client_name, key))
            for key in repo.get_allowed_client_keys()
            if key != obnamlib.REPO_CLIENT_TEST_KEY
            )

    def dump_client_generation_ids(self, repo, client_name):
        return [
            repo.make_generation_spec(gen_id)
            for gen_id in repo.get_client_generation_ids(client_name)
            ]

    def dump_generation(self, repo, client_name, gen_id):
        obj = {
            'client-name': client_name,
            'generation-id': repo.make_generation_spec(gen_id),
            'generation-keys': self.dump_generation_keys(repo, gen_id),
            'generation-chunk-ids':
                self.dump_generation_chunk_ids(repo, gen_id),
            }
        if self.app.settings['dump-repo-file-metadata']:
            obj['files'] = self.dump_generation_files(repo, gen_id)
        return obj

    def dump_generation_keys(self, repo, gen_id):
        return dict(
            (obnamlib.repo_key_name(key),
             repo.get_generation_key(gen_id, key))
            for key in repo.get_allowed_generation_keys()
            if key != obnamlib.REPO_GENERATION_TEST_KEY
            )

    def dump_generation_chunk_ids(self, repo, gen_id):
        return repo.get_generation_chunk_ids(gen_id)

    def dump_generation_files(self, repo, gen_id):
        result = {}
        for filename in repo.walk_generation(gen_id, '/'):
            result[filename] = {
                'file-chunk-ids': repo.get_file_chunk_ids(gen_id, filename),
                'file-keys': self.dump_file_keys(repo, gen_id, filename),
                }
        return result

    def dump_file_keys(self, repo, gen_id, filename):
        return dict(
            (obnamlib.repo_key_name(key),
             repo.get_file_key(gen_id, filename, key))
            for key in repo.get_allowed_file_keys()
            if key != obnamlib.REPO_FILE_TEST_KEY
            )
