# DIP mungers!

We created these at SFU Archives in order to support ad-hoc DIP upload and metadata updates from Archivematica to AtoM at points in our workflow not supported by the existing [AtoM DIP upload functionality](https://www.archivematica.org/en/docs/archivematica-1.10/user-manual/access/access/#upload-atom).

If you plan to use these scripts, I encourage you to compile them for your local environment with `pyinstaller`, so that their dependencies are packaged in and they can be run like command line programs rather than Python scripts. This needs to be done separately for Windows, Mac, and Linux environments. Many of the server *names* are currently hardcoded to SFU Archives' environment but the paths themselves are all as generic as possible.

## Installation

1. Clone this repo:

```bash
git clone https://github.com/axfelix/dip-mungers
cd dip-mungers
```

2. Copy configuration file to expected location:

```bash
cp dip-mungers-config.ini ~/.dip-mungers
```

3. Open configuration file and set values:

```bash
nano ~/.dip-mungers
```

4. Install Python package

```bash
pip install .
```

When installation is cmoplete, three new command-line scripts will be available: `dip-retrieve`, `dip-metadata`, and `dip-upload`.

## Usage

### Retrieval

There are three scripts in this repository. `dip-retrieve` is used to fetch DIPs that have been stored by Archivematica as a first step; this workflow always assumes that you are storing your DIPs in the Archivematica Storage Service. It takes the AIP's UUID as an argument, and downloads the associated DIP via the Storage Service API.

e.g.

```bash
dip-retrieve 6f8e97bc-e21b-4b6f-a8a0-cc98aaf8d920
```

To use download DIPs from the development Storage Service rather than production, use the `--dev` flag.

### Upload

From here, you can either upload an entire DIP, or -- in cases where you do not want to make objects available via AtoM but wish to provide metadata stubs for users browsing your repository -- just its metadata. In either case, you'll want to manually populate the 'slug' column of the spreadsheet consistent with [the AtoM documentation for manually uploading DIP objects](https://www.accesstomemory.org/en/docs/2.5/admin-manual/maintenance/cli-tools/#manually-upload-archivematica-dip-objects). The `dip-upload` script otherwise follows this workflow exactly by performing the scp transfer step on the server for you and cleaning up afterwards.

Your SFU user account will need sudo rights on the AtoM server. To avoid this, you can pass the `--nginx` argument to use the `nginx` user for the DIP upload rather than your SFU user account. The `--nginx` option will only work if your SSH key is on the jump server.

e.g.

```bash
dip-metadata ~/Desktop/my-local-dip
```

The `dip-metadata` script uses the same syntax and the same input but instead of adding entire objects to AtoM, it only sends new metadata to AtoM's API based on the METS files packaged in with the DIP, using Artefactual's [agentarchives](https://github.com/artefactual-labs/agentarchives) API library. Rather than configuring ssh authentication, it requires you to [configure an AtoM API key](https://www.accesstomemory.org/en/docs/2.5/dev-manual/api/api-intro/#authentication). It currently supports adding filenames, filesizes, object types, and UUIDs for every child of a DIP object to a parent record in AtoM; no other metadata is supported due to API limitations.

e.g.

```bash
dip-upload ~/Desktop/my-local-dip
```

To use upload DIPs by either method to the development AtoM rather than production, use the `--dev` flag.


## Acknowledgements

This repository contains source code from [paramiko-jump](https://github.com/andrewschenck/paramiko-jump). Copyright 2020, Andrew Blair Schenck, licensed under the Apache License, Version 2.0.
