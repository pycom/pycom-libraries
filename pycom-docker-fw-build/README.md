<p align="center"><img src ="https://github.com/pycom/pycom-libraries/blob/master/img/logo.png" width="300"></p>

# Tool for adding your MicroPython code frozen in the flash

### usage:
```
sudo docker run -v `pwd`:/opt/frozen -it goinvent/pycom-fw build board-type your-project-version-code [micropython-sigfox-git-tag] [esp-idf-git-tag]
```
where board in `WIPY LOPY SIPY GPY FIPY LOPY4` and your-project-version-code is a tag for output file: `LOPY4-your-project-version-code.tar.gz`


### example:

If you have your MicroPython project in the current directory `.` just type:

```
sudo docker run -v `pwd`:/opt/frozen -it goinvent/pycom-fw  build LOPY4 myproject
```
For building against a specific revision (ex:v1.20.0.rc0 idf_v3.1) you can use:
```
sudo docker run -v `pwd`:/opt/frozen -it goinvent/pycom-fw  build FIPY myproject v1.20.0.rc0 idf_v3.1
```


### note:

The Frozen code implementation might not support sub-directories in MicroPython code.

The Frozen code implementation does not support adding assets (ex: db files, json,)

### re-generate this goinvent/pycom-fw docker image:

```
sudo docker build -t goinvent/pycom-fw  .
```
