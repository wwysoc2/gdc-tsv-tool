import sys
import json
import requests
import re
import argparse


def arg_parse():
    parser = argparse.ArgumentParser(
		description='----GDC Metadata TSV Download Tool v2.0----',
		usage= 'python gdc-tsv-tool.py <options> MANIFEST_FILE')
    parser.add_argument('-o','--output', metavar='FILE_PREFIX',
		action="store", dest='o', type=str, default="metadata",
		help='Designates a prefix for output files')
    parser.add_argument('-c','--clinical', action="store_true",
		help='Only outputs clinical metadata')
    parser.add_argument('-b','--biospecimen', action="store_true",
		help='Only outputs biospecimen metadata')
    parser.add_argument('-u','--uuid_list', action="store_false",
		help='Pass a plain text list of UUIDs ' \
		'(one UUID per line) instead of a manifest')
    parser.add_argument('-l','--legacy', action="store_true",
		help='Manifest from GDC Legacy Archive')
    parser.add_argument('-s','--simple', action="store_true",
		help='Output a simple set of fields' \
		'(file name, file id, project id, ' \
		'case barcode, sample type)')
    parser.add_argument('-x','--mafout', action="store_true",
		help='Output separate metadata file for ' \
		'MAF or XLSX file (warning: messy)')
    parser.add_argument('-a','--allop', action="store_true",
		help='Empty or datetime columns are not removed' \
		' from the output file')
    parser.add_argument('manifest_file', action="store",
		help='Path to manifest file (or UUID List with -u)')
    args = parser.parse_args()
    return args

def error_parse(code):
	'''
	Generates the error messages
	'''
	error = {
		"bad_mani":"Input must be valid GDC Manifest. " \
		"\n\tGo to https://portal.gdc.cancer.gov/ to download a manifest",
		"no_result":"Query produced no results, " \
		"are these files from the Legacy Archive? (use -l)"
	}
	print("ERROR : " + error[code])
	sys.exit(2)

def verbose():
	'''
	Generates the running messages
	'''
	global get_clin, get_bio, maf_info, is_manifest
	message = '\n'
	if sim_arg == True:  message += ">-- Retrieving basic metadata\n"
	if get_clin == True: message += ">-- Retrieving clinical metadata\n"
	if get_bio  == True: message += ">-- Retrieving biospecimen metadata\n"
	if maf_info == True: message += ">-- Retrieving MAF/XLSX metadata\n"
	print(message)
	print("***************************************\n")

def main(args):
	'''
	Retrieves and parses the arguments
	'''
	global get_clin, get_bio, maf_info, is_manifest, bio_arg, clin_arg,\
	sim_arg, all_columns, o_filename, legacy, manifest_file
	maf_info = args.mafout
	is_manifest = args.uuid_list
	bio_arg = args.biospecimen
	clin_arg = args.clinical
	sim_arg = args.simple
	all_columns = args.allop
	o_filename = args.o
	legacy = args.legacy
	manifest_file = args.manifest_file
	get_clin = True; get_bio = True
	if bio_arg == True: get_clin = False
	if clin_arg == True: get_bio = False
	if bio_arg == True and clin_arg == True: get_bio = True; get_clin = True
	if sim_arg == True: get_bio = False; get_clin = False

def get_uuid_list(manifest):
	'''
	Retrieves thes list of UUIDs from
	the manifest passed to the script
	'''
	with open(manifest,'r') as myfile:
		uuid_dict = {}
		if is_manifest == True:
			if myfile.readline()[0:2] != 'id': error_parse("bad_mani")
			for x in myfile:
				uuid = x.split('\t')[0]
				file_name = x.split('\t')[1]
				uuid_dict[uuid] = file_name
		else:
			for x in myfile:
				uuid = x.strip()
				file_name = ''
				uuid_dict[uuid] = file_name
	return uuid_dict

def classify_file_list(file_dict):
	'''
	Mixing files with different numbers of aliquots can be messy.
	This function separates all of the files into 'mono' , 'di',
	and 'poly' -aliquots by reading their extension on the filename.
	'''
	mono,poly,di = [],[],[]

	if is_manifest == True:
		for uuid in file_dict.keys():
			filename = file_dict[uuid].strip()
			extension = filename.split(".")[-1]
			if extension == 'gz':
				extension = filename.split(".")[-2]
				if extension == 'maf' or extension == 'xlsx':
					poly.append(uuid)
				elif extension == 'vcf': di.append(uuid)
				else: mono.append(uuid)
			elif extension == 'vcf': di.append(uuid)
			elif extension == 'maf': poly.append(uuid)
			else: mono.append(uuid)
	else:
		for uuid in file_dict.keys(): mono.append(uuid)
	return mono,di,poly

def retrieve_metadata_for_list(file_list):
	'''
	This function makes the API call based on a list of UUIDs
	and arguments (clinical, biospecimen, etc)
	'''
	headers = {'Content-Type': 'application/json'}
	url = 'https://api.gdc.cancer.gov/files'
	if legacy == True: url = 'https://api.gdc.cancer.gov/legacy/files'
	fields =  "file_id,file_name,cases.submitter_id,cases.samples.sample_type," \
		"cases.project.project_id,cases.project.name"
	expand = ""
	if get_clin == True:
		expand += "cases,cases.demographic,cases.exposures," \
			"cases.diagnoses,cases.diagnoses.treatments," \
			"cases.diagnoses,cases.family_histories,"
	if get_bio == True:
		expand += "cases,cases.samples,cases.samples.portions," \
			"cases.samples.portions.analytes," \
			"cases.samples.portions.analytes.aliquots," \
			"cases.samples.portions.slides," \
			"analysis.metadata.read_groups"
   	params = {"filters":
		{"op":"in","content":
		{"field":"file_id", "value":file_list}},
        "format":"TSV", "fields":fields,
        "expand":expand,"size": "10000"}
	response = requests.post(url, data=json.dumps(params), headers=headers, stream=True)
	if len(response.content.strip()) == 0: error_parse("no_result")
	return response.content

def order_columns(matrix_list):
	'''
	Note: This function is used in the clean_matrix function
	It puts the columns in a somewhat desirable order
	'''
	new_matrix = []
	nmdict = {}
	# Special fields go first
	special = ["file_name", "file_id","project_project_id","project_name"]
	# This step looks at the_order and rearranges the column based on
	# their entity-of-origin
	the_order = ["special","cases","samples", "portions", "analytes",
				"aliquots","slides","demographic", "exposures","diagnoses",
				"treatments","family_histories","analysis_metadata_read_groups"]
	clinfields = ["demographic", "exposures","treatments",
					"diagnoses","family_histories","cases"]
	biofields = ["samples", "portions", "analytes","aliquots","slides",
					"analysis_metadata_read_groups","project"]
	donefields = []
	nmdict["special"] = []
	for item in special:
		for j in matrix_list:
			col_name = j[0]
			if item in col_name:
				nmdict["special"].append(j)
				donefields.append(j)
	for item in biofields:
		subid = []
		nmdict[item] = []
		for j in matrix_list:
			col_name = j[0]
			ents = re.split('_[0-9]_',col_name)
			if len(ents) > 1:
				last_ent = ents[-2]
				if item == last_ent and (j not in donefields):
					# Adding submitter_id to be start of entity
					if "submitter_id" in col_name:
						subid.append(j)
						donefields.append(j)
					else:
						nmdict[item].append(j)
						donefields.append(j)
		if len(subid) > 0: nmdict[item] = subid + nmdict[item]
	for item in clinfields:
		nmdict[item] = []
		for j in matrix_list:
			col_name = j[0]
			if item in col_name and (j not in donefields):
				if "submitter_id" in col_name:
					subid.append(j)
					donefields.append(j)
				else:
					nmdict[item].append(j)
					donefields.append(j)
		if len(subid) > 0:
			nmdict[item] = subid + nmdict[item]
			subid = []
	for item in the_order: new_matrix += nmdict[item]

	# Adding remainder of fields to the matrix
	for j in matrix_list:
		if j not in donefields:
			new_matrix.append(j)
	return new_matrix

def clean_matrix(testcase):
	'''
	Removes empty columns and datetime columns (unless -a is specified)
	'''
	global all_columns
	matrix = []
	# Turning output into list of lists (matrix)
	testcase = testcase.decode().strip().split('\n')
	for row in testcase:
		row = row.replace('\r','')
		row_list = row.split('\t')
		matrix.append(row_list)

	columns = zip(*matrix)
	# The good_cols list will contain the transposed columns
	good_cols = []
	for column in columns:
		column = list(column)
		col_name = column[0]
		if (len(list(filter(lambda x: x != 'live',(filter(None,column))))) > 1 \
        and 'datetime' not in col_name) or all_columns == True:
			good_cols.append(column)
	good_cols = order_columns(good_cols)
	clean_matrix = zip(*good_cols)
	inter_matrix = []
	for row in clean_matrix: inter_matrix.append('\t'.join(row))
	final_matrix = '\n'.join(inter_matrix)
	return final_matrix

def run_main(my_list, extension, file_type):
	fn = o_filename + extension
	with open(fn,'w') as my_file:
		matrix = retrieve_metadata_for_list(my_list)
		my_file.write(clean_matrix(matrix))
	print(">-- {} file metadata written to {}\n".format(file_type,fn))

main(arg_parse())

uuid_dictionary = get_uuid_list(str(manifest_file))
mono,di,poly = classify_file_list(uuid_dictionary)
master = [(mono,".files.txt","Standard"),
	(di,".vcfs.txt","VCF"),
	(poly,".mafs.txt","MAF/XLSX")]

# Checks to see if each subset of files is actually present.
# Then it performs the query and writes it to the file.
# If the query returned nothing, print an error

if len(mono) + len(di) + len(poly) == 0: error_parse("no_result")
verbose()
for my_list, extension, file_type in master[:2]:
	if len(my_list) > 0:
		run_main(my_list, extension, file_type)
if maf_info == True:
	for my_list, extension, file_type in master[2:]:
		if len(my_list) > 0:
			run_main(my_list, extension, file_type)
