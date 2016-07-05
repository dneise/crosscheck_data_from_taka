all: local global
	bash pandoc_cmd.sh

local: local_tc.csv local_tc_fake.csv local_tc.png local_tc_fake.png 

global: global_tc.csv global_tc_fake.csv global_tc.png global_tc_fake.png

global_tc.csv:
	python calc_global_tc.py -o global_tc.csv

global_tc.png: global_tc.csv
	python plot_tc.py global_tc.csv

global_tc_fake.csv: local_tc.csv
	python calc_global_tc.py --fake -o global_tc_fake.csv

global_tc_fake.png: global_tc_fake.csv
	python plot_tc.py global_tc_fake.csv

local_tc.csv:
	python calc_local_tc.py -o local_tc.csv

local_tc_fake.csv: local_tc.csv
	python calc_local_tc.py --fake -o local_tc_fake.csv

local_tc.png: local_tc.csv
	python plot_tc.py local_tc.csv

local_tc_fake.png: local_tc_fake.csv
	python plot_tc.py local_tc_fake.csv


clean:
	rm -f local_tc.csv local_tc_fake.csv global_tc.csv global_tc_fake.csv
	rm -f local_tc.png local_tc_fake.png global_tc.png global_tc_fake.png
	rm -f report.pdf