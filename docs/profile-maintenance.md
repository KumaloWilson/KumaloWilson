# Maintaining the profile

Edit `profile.config.json`, then run:

```sh
python3 scripts/gen_profile.py
```

This rebuilds `README.md` and the SVG cards in `assets/stage/` from the saved
GitHub data in `assets/profile.json`. Python 3 is the only dependency. Commit
the config, scripts, README, and generated assets together; the checked-in
cards render immediately without waiting for an Action or external image API.

## Refreshing GitHub data

The **Refresh profile** workflow runs daily at 04:00 UTC (06:00 in Zimbabwe),
when its config or scripts change on `main`, or manually from the Actions tab.
It uses the repository's built-in `GITHUB_TOKEN`; no additional secret is needed.
Repository Actions settings must allow workflows to write repository contents.
Protected branches may require the automated commits to go through a PR instead.

For a local refresh, provide `GH_TOKEN`, `GITHUB_TOKEN`, or `STATS_TOKEN` in
your environment, then run:

```sh
python3 scripts/fetch_profile_data.py
python3 scripts/gen_profile.py
python3 -m unittest discover -s tests
```

Stats include public repositories, stars on public repositories, followers, and
all-time contributions across each year since the account was created. The hero
shows total calendar contributions; the activity card also shows visible commits,
pull requests, PR reviews, issues opened, and anonymous private activity.

To include anonymous private activity without adding a personal token, open your
GitHub profile, then **Contribution settings → Private contributions**, and enable
it. [GitHub's instructions](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/manage-visibility-settings-for-private-contributions-and-achievements)
explain this account setting. The workflow cannot enable it for you. Hidden
private contribution counts cannot be retrieved without suitable access.

Calendar totals already include the private contributions GitHub exposes, so
the fetcher does not add the anonymous count again. Anonymous private activity
includes several contribution types and is never added to the commit count.
The anonymous figure is GitHub's `restrictedContributionsCount`: shared activity
the current token cannot inspect. Visible breakdowns depend on token access and
GitHub contribution rules; they do not promise a private breakdown by type.
An optional `STATS_TOKEN` can provide broader visibility but is not required.

## Personalization

The cobalt accent (`#0F57BE`) is sampled from Wilson’s LinkedIn cover and is
configured in `accent_color`. Projects follow the order in `targets`, with
Neotree first, followed by IoT attendance, ZINWA water meters, CUT analytics,
and the rest of the portfolio.

- `targets` selects public repositories to display. Set `label`, `tag`, `url`,
  `description`, or `wip` to override the fetched project metadata. Use `owner`
  for organization projects such as `neotree/neotree`. Organization project stars
  belong to that project and are not added to your personal GitHub totals.
- `contacts` and `badges` control the links below the project cards.
- `posts.count` is currently zero. To show writing, set a positive count and
  supply an RSS 2.0 feed in `posts.feed_url`. The section is hidden when empty.
- `ticker_message` controls the scrolling message beneath the contact cards.
- SVG animation respects the viewer's reduced-motion preference.

The old banner, skill GIFs, quote dataset, and HTML snapshots are retained as
legacy assets. `update-quote.js` belongs to the previous README design and is
not part of the new generation process. The existing snake workflow still
maintains its `output` branch independently.

## Design source

Adapted from [KumaloWilson/basteez](https://github.com/KumaloWilson/basteez),
originally [basteez/basteez](https://github.com/basteez/basteez), at commit
`25d3db1be40e5ca72cb3aba0018c31c071522011`.
The profile generator, data fetcher, and workflow were personalized for Wilson
Kumalo. The generated README retains a design credit.
