import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


def load_fetcher():
    spec = importlib.util.spec_from_file_location('fetch_profile', ROOT / 'scripts/fetch_profile_data.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.sources.append(dict(attrs)['src'])


class ProfileTests(unittest.TestCase):
    def test_generation_escapes_text_and_omits_disabled_posts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            (root / 'assets').mkdir()
            shutil.copy(ROOT / 'scripts/gen_profile.py', root / 'scripts')
            config = json.loads((ROOT / 'profile.config.json').read_text())
            config['about'] = 'Systems & software <engineer> "Wilson"'
            (root / 'profile.config.json').write_text(json.dumps(config))
            data = {'stats': {'commits': 12, 'stars': 3, 'repos': 5, 'followers': 2,
                              'contributions': 120, 'private_contributions': 99,
                              'pull_requests': 4, 'reviews': 3, 'issues': 2},
                    'repos': {}, 'posts': [{'title': 'Old post', 'url': 'https://example.com', 'date': '2026-01-01'}]}
            (root / 'assets/profile.json').write_text(json.dumps(data))
            command = ['python3', str(root / 'scripts/gen_profile.py')]
            subprocess.run(command, check=True, capture_output=True)
            readme = (root / 'README.md').read_text()
            self.assertNotIn('h-intel.svg', readme)
            self.assertNotIn('github.com/basteez/local_genai', readme)
            self.assertIn('github.com/KumaloWilson/local_genai', readme)
            self.assertIn('https://github.com/neotree/neotree', readme)
            self.assertLess(readme.index('NEOTREE'), readme.index('IOT ATTENDANCE'))
            parser = Images()
            parser.feed(readme)
            for source in parser.sources:
                if not source.startswith('https://'):
                    ET.parse(root / source)
            before = {p.name: p.read_bytes() for p in (root / 'assets/stage').glob('*.svg')}
            self.assertIn(b'#0F57BE', before['hero.svg'])
            self.assertNotIn(b'#e60012', b''.join(before.values()))
            self.assertIn(b'Map-based taxi booking', before['target-11.svg'])
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(readme, (root / 'README.md').read_text())
            self.assertEqual(before, {p.name: p.read_bytes() for p in (root / 'assets/stage').glob('*.svg')})

    def test_disabled_feed_does_not_make_network_request(self):
        fetcher = load_fetcher()
        with patch.object(fetcher.urllib.request, 'urlopen', side_effect=AssertionError('Unexpected request')):
            self.assertEqual(fetcher.fetch_posts(), [])

    def test_organization_project_uses_its_own_owner(self):
        fetcher = load_fetcher()
        project = {'stargazerCount': 8, 'description': 'Neonatal care',
                   'url': 'https://github.com/neotree/neotree', 'primaryLanguage': None}
        with patch.object(fetcher, 'TARGETS', [{'repo': 'neotree', 'owner': 'neotree'}]), \
                patch.object(fetcher, 'gql', return_value={'repository': project}) as request:
            result = fetcher.fetch_repos()
            self.assertEqual(request.call_args.args[1], {'o': 'neotree', 'n': 'neotree'})
            self.assertEqual(result['neotree']['url'], project['url'])

    def test_commit_count_excludes_other_restricted_contributions(self):
        fetcher = load_fetcher()

        def fake_gql(query, variables):
            if 'createdAt' in query:
                return {'user': {'createdAt': '2026-01-01', 'followers': {'totalCount': 2},
                                 'repositories': {'totalCount': 4}}}
            if 'stargazerCount' in query:
                return {'user': {'repositories': {'nodes': [{'stargazerCount': 3}],
                                                 'pageInfo': {'hasNextPage': False}}}}
            return {'user': {'contributionsCollection': {'totalCommitContributions': 10,
                                                        'restrictedContributionsCount': 99,
                                                        'totalPullRequestContributions': 4,
                                                        'totalPullRequestReviewContributions': 3,
                                                        'totalIssueContributions': 2,
                                                        'contributionCalendar': {'totalContributions': 120}}}}

        with patch.object(fetcher, 'gql', side_effect=fake_gql):
            result = fetcher.fetch_stats()
            years = fetcher.datetime.datetime.now(fetcher.datetime.timezone.utc).year - 2025
            self.assertEqual(result['commits'], 10 * years)
            self.assertEqual(result['private_contributions'], 99 * years)
            self.assertEqual(result['contributions'], 120 * years)
            self.assertEqual(result['pull_requests'], 4 * years)
            self.assertEqual(result['reviews'], 3 * years)
            self.assertEqual(result['issues'], 2 * years)


if __name__ == '__main__':
    unittest.main()
