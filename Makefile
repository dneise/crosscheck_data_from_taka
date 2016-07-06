all: local global qr
	bash pandoc_cmd.sh

local: local_tc.csv local_tc_fake.csv local_tc.png local_tc_fake.png charge_resolution_local_tc.png

global: global_tc.csv global_tc_fake.csv global_tc.png global_tc_fake.png charge_resolution_global_tc.png

qr: qr_tc.csv qr_tc_fake.csv qr_tc.png qr_tc_fake.png charge_resolution_qr_tc.png

qr_tc.csv:
	python calc_qr_tc.py -o qr_tc.csv

qr_tc_fake.csv:
	python calc_qr_tc.py --fake -o qr_tc_fake.csv -i local_tc.csv

qr_tc.png: qr_tc.csv
	python plot_tc.py qr_tc.csv

qr_tc_fake.png: qr_tc_fake.csv
	python plot_tc.py qr_tc_fake.csv

charge_resolution_qr_tc.png: qr_tc.csv
	python extract_pulses.py --tc qr_tc.csv

global_tc.csv:
	python calc_global_tc.py -o global_tc.csv

global_tc.png: global_tc.csv
	python plot_tc.py global_tc.csv

global_tc_fake.csv: local_tc.csv
	python calc_global_tc.py --fake -o global_tc_fake.csv -i local_tc.csv

global_tc_fake.png: global_tc_fake.csv
	python plot_tc.py global_tc_fake.csv

local_tc.csv:
	python calc_local_tc.py -o local_tc.csv

local_tc_fake.csv: local_tc.csv
	python calc_local_tc.py --fake -o local_tc_fake.csv -i local_tc.csv

local_tc.png: local_tc.csv
	python plot_tc.py local_tc.csv

local_tc_fake.png: local_tc_fake.csv
	python plot_tc.py local_tc_fake.csv

charge_resolution_local_tc.png: local_tc.csv
	python extract_pulses.py --tc local_tc.csv 

charge_resolution_global_tc.png: global_tc.csv
	python extract_pulses.py --tc global_tc.csv 


clean:
	rm -f local_tc.csv local_tc_fake.csv global_tc.csv global_tc_fake.csv
	rm -f local_tc.png local_tc_fake.png global_tc.png global_tc_fake.png
	rm -f charge_resolution_local_tc.png charge_resolution_global_tc.png 
	rm -f time_resolution_local_tc.png time_resolution_global_tc.png 
	rm -f qr_tc.csv qr_tc_fake.csv qr_tc.png qr_tc_fake.png charge_resolution_qr_tc.png
	rm -f report.pdf