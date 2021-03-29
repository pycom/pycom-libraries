release: clean pysense pysense2 pytrack pytrack2 pyscan
PYBYTES ?= 0


pysense:
	@echo "Making Pysense"
	mkdir pysense
	mkdir pysense/lib
	# sensors
	cp shields/lib/LIS2HH12.py pysense/lib/
	cp shields/lib/LTR329ALS01.py pysense/lib/
	cp shields/lib/MPL3115A2.py pysense/lib/
	cp shields/lib/SI7006A20.py pysense/lib/
	# pycoproc
	cp shields/lib/pycoproc_1.py pysense/lib/
	# example
ifeq ($(PYBYTES), 1)	
	$(info PYBYTES enabled)
	cp shields/pysense_1_pybytes.py pysense/main.py
else
	cp shields/pysense_1.py pysense/main.py
endif
	zip -r pysense.zip pysense

pysense2:
	@echo "Making Pysense 2"
	mkdir pysense2
	mkdir pysense2/lib
	# sensors
	cp shields/lib/LIS2HH12.py pysense2/lib/
	cp shields/lib/LTR329ALS01.py pysense2/lib/
	cp shields/lib/MPL3115A2.py pysense2/lib/
	cp shields/lib/SI7006A20.py pysense2/lib/
	# pycoproc
	cp shields/lib/pycoproc_2.py pysense2/lib/
	# example
ifeq ($(PYBYTES),1)
	cp shields/pysense_2_pybytes.py pysense2/main.py
else
	cp shields/pysense_2.py pysense2/main.py
endif
	zip -r pysense2.zip pysense2

pytrack:
	@echo "Making Pytrack"
	mkdir pytrack
	mkdir pytrack/lib
	#sensors
	cp shields/lib/L76GNSS.py pytrack/lib/
	cp shields/lib/LIS2HH12.py pytrack/lib/
	#pycoproc
	cp shields/lib/pycoproc_1.py pytrack/lib/
	#example
ifeq ($(PYBYTES),1)
	cp shields/pytrack_1_pybytes.py pytrack/main.py
else
	cp shields/pytrack_1.py pytrack/main.py
endif
pytrack2:
	@echo "Making Pytrack2"
	mkdir pytrack2
	mkdir pytrack2/lib
	#sensors
	cp shields/lib/L76GNSS.py pytrack2/lib/
	cp shields/lib/LIS2HH12.py pytrack2/lib/
	#pycoproc
	cp shields/lib/pycoproc_2.py pytrack2/lib/
	#example
ifeq ($(PYBYTES),1)
	cp shields/pytrack_2_pybytes.py pytrack2/main.py
else
	cp shields/pytrack_2.py pytrack2/main.py
endif

pyscan:
	@echo "Making Pyscan"
	mkdir pyscan
	mkdir pyscan/lib
	#sensors
	cp shields/lib/LIS2HH12.py pyscan/lib/
	cp shields/lib/MFRC630.py pyscan/lib/
	cp shields/lib/SI7006A20.py pyscan/lib/
	cp shields/lib/LTR329ALS01.py pyscan/lib/
	#pycoproc
	cp shields/lib/pycoproc_1.py pyscan/lib/
	#example
	cp shields/pyscan_1.py pyscan/main.py	

clean:
	@echo "Cleaning up files"
	rm -rf pysense
	rm -rf pytrack
	rm -rf pyscan
	rm -rf pysense2
	rm -rf pytrack2
	rm -f pysense.zip
	rm -f pysense2.zip
	rm -f pytrack.zip
	rm -f pytrack2.zip
	rm -f pyscan.zip


