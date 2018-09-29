<p align="center"><img src ="https://github.com/pycom/pycom-libraries/blob/master/img/logo.png" width="300"></p>

# Tool for adding your MicroPython code frozen in the flash

### usage:
```
 docker run -v `pwd`:/opt/frozen -it goinvent/pycom-fw build board your-project stable|development
```
where board in `WIPY LOPY SIPY GPY FIPY LOPY4` and your-project is a tag for output file: `firmware-your-project.tar.gz`


### example:

If you have your MicroPython project in the current directory `.` just type:

```
  docker run -v `pwd`:/opt/frozen -it goinvent/pycom-fw  build LOPY4 myproject stable
```

### note:

The Frozen code implementation does not support sub-directories in MicroPython code.

The Frozen code implementation does not support adding assets (ex: db files, json,)


### re-generate this goinvent/pycom-fw docker image:

```
docker build -t goinvent/pycom-fw  .
```
