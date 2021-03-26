
release: pysense pysense2 


pysense:
	mkdir pysense
	mkdir pysense/lib
	# sensors
	cp shields/lib/LIS2HH12.py pysense/lib/
	cp shields/lib/LTR329ALS01.py pysense/lib/
	cp shields/lib/MPL3115A2.py pysense/lib/
	cp shields/lib/SI7006A20.py pysense/lib/
	# pycoproc
	cp shields/lib/pycoproc_1.py pysense/lib/pycoproc.py
	# example
	cp shields/pysense_1.py pysense/main.py
	zip -r pysense.zip pysense

pysense2:
	mkdir pysense2
	mkdir pysense2/lib
	# sensors
	cp shields/lib/LIS2HH12.py pysense2/lib/
	cp shields/lib/LTR329ALS01.py pysense2/lib/
	cp shields/lib/MPL3115A2.py pysense2/lib/
	cp shields/lib/SI7006A20.py pysense2/lib/
	# pycoproc
	cp shields/lib/pycoproc.py pysense/lib/pycoproc.py
	# example
	cp shields/pysense_2.py pysense/main.py
	zip -r pysense2.zip pysense2

clean:
	@echo "Cleaning up files"
	rm -rf pysense
	rm -rf pytrack
	rm -rf pyscan
	rm -rf pysense2
	rm -rf pytrack2
	
