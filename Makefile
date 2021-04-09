release: pyscan pysense pysense2 pytrack pytrack2 


pyscan:
	rm -rf pyscan
	rm -f pyscan.zip
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

	zip -r pyscan.zip pyscan

pysense:
	rm -rf pysense
	rm -f pysense.zip
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
	cp shields/pysense_1.py pysense/main.py

	zip -r pysense.zip pysense

pysense2:
	rm -rf pysense2
	rm -f pysense2.zip
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
	cp shields/pysense_2.py pysense2/main.py

	zip -r pysense2.zip pysense2

pytrack:
	rm -rf pytrack
	rm -f pytrack.zip
	@echo "Making Pytrack"
	mkdir pytrack
	mkdir pytrack/lib
	#sensors
	cp shields/lib/L76GNSS.py pytrack/lib/
	cp shields/lib/LIS2HH12.py pytrack/lib/
	#pycoproc
	cp shields/lib/pycoproc_1.py pytrack/lib/
	#example
	cp shields/pytrack_1.py pytrack/main.py

	zip -r pytrack.zip pytrack

pytrack2:
	rm -rf pytrack2
	rm -f pytrack2.zip
	@echo "Making Pytrack2"
	mkdir pytrack2
	mkdir pytrack2/lib
	#sensors
	cp shields/lib/L76GNSS.py pytrack2/lib/
	cp shields/lib/LIS2HH12.py pytrack2/lib/
	#pycoproc
	cp shields/lib/pycoproc_2.py pytrack2/lib/
	#example
	cp shields/pytrack_2.py pytrack2/main.py
	
	zip -r pytrack2.zip pytrack2

clean:
	@echo "Cleaning up files"
	rm -rf pyscan
	rm -rf pysense
	rm -rf pysense2
	rm -rf pytrack
	rm -rf pytrack2

	rm -f pyscan.zip
	rm -f pysense.zip
	rm -f pysense2.zip
	rm -f pytrack.zip
	rm -f pytrack2.zip