=======
GraceDB
=======

.. automodule:: bilby_pipe.gracedb

Command line interface to create ini file for GraceDB event
-----------------------------------------------------------

The :code:`bilby_pipe_gracedb` command line program provides a method 
to generate ini files for a GraceDB event. This ini file can then be 
used as the input for the other bilby_pipe modules. 

.. argparse::
   :module: bilby_pipe.gracedb
   :func: create_parser
   :prog: fancytool
