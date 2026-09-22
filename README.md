# DRockRadio V1 — Database Maintenance

This repository is intended for the **central maintenance of the official DRockRadio station database**.

The customer application remains unchanged. The repository is responsible for:

- recurring health checks of the 300 official stations;
- keeping a history of failures instead of reacting to one temporary outage;
- querying Radio Browser for possible replacement stream URLs;
- verifying a candidate stream before it can replace a current URL;
- preserving the stable DRR-xxxx station IDs;
- publishing `stations.json` and a SHA-256 manifest for DRockRadio Database Update.

## Safety rules

1. Never delete a station because of one failed check.
2. Never replace a stream URL only because Radio Browser has a matching name.
3. A candidate must have a strong station match and must respond to a direct stream test.
4. If the evidence is insufficient, leave the existing record unchanged and report it for review.
5. My Stations and Favorites are local application data and are not touched by this repository.

## Public delivery

The intended public files are:

- `data/manifest.json`
- `data/stations.json`

After the repository is created, these can be served over HTTPS through GitHub's public raw file URLs. The application will use the manifest URL; it will not need GitHub-specific logic.

## Current database

The supplied database is the currently approved 300-station database from DRockRadio V1. No station is removed by this maintenance package.
