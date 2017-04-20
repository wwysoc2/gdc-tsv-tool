# GDC Spreadsheet Download Tool

The GDC Spreadsheet Download Tool will download clinical and/or biospecimen metadata for a given set of files in a tab-delimited format. These file sets can be passed to the tool in a manifest downloaded from the GDC Portal (https://portal.gdc.cancer.gov/) or in a plain text list of file UUIDs. The tab delimited output is compatible with Microsoft Excel or any other spreadsheet program.  

The GDC Spreadsheet Download Tool produces TSVs in which each row represents one file and each column represents a clinical or biospecimen field. Because of the structure of the GDC Data Model, files can be associated with more than one of each field (e.g. a VCF associated with a tumor sample and a normal sample), which produces more than one column. This tool divides the TSV into smaller TSVs of equal column number.

Usage: python gdc-tsv-tool.py <options> <manifest_file>

Options:
* -h, --help : Displays documentation
* -o, --output : Designate prefix for output files (Default: metadata)
* -c, --clinical : Outputs clinical metadata
* -b, --biospecimen : Outputs biospecimen metadata
* -u, --uuid-list : Passing UUID List instead of manifest
* -l, --legacy : Manifest from GDC Legacy Archive
* -s, --simple : Output a simple set of fields (file name, file id, project id, case barcode, sample type)
* -x, --mafout: Output separate metadata file for MAF or XLSX file (warning: messy)
* -a, --allop: Output does not remove empty or datetime columns

Notes:
* The default parameters produce both clinical and biospecimen data, which is the same as passing both -c and -b.
* Passing the simple (-s) argument overrides both the clinical (-c) and biospecimen (-b) arguments.
