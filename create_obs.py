#!/usr/bin/env python
#coding: utf8
"""Generate and send GRAVITY OBs to P2

The create_obs script is used to generate GRAVITY OBs and send them to P2
To use this script, you need to call it with a YML file, see example below.

Authors:
  M. Nowak, and the exoGravity team.
"""

# import sys for args
import sys
sys.path.append('/Users/wbalmer/')
# import ESO P2 api and getpass to manage user password
import p2api
from getpass import getpass

# ruamel or yaml to read config yml file
import ruamel.yaml as yaml
    
# import this package
import p2Gravity as p2g
from p2Gravity.common import *
from p2Gravity.plot import *

# import sys and argparse for args
import sys
import argparse

# create the parser for command lines arguments
parser = argparse.ArgumentParser(description=
"""
Generate and send GRAVITY OBs to P2
""")

# required arguments are the path to the folder containing the data, and the path to the config yml file to write 
parser.add_argument('file', type=str, nargs="?", help="the path the to input YAML configuration file (or output when using --generate).")

# some optional arguments
parser.add_argument("--generate", metavar="TYPE", type=str, default=argparse.SUPPRESS, choices=["dual_on", "dual_off", "dual_off_calib", "dual_wide_off", "dual_wide_on", "single_on"], nargs = 1,
                    help="if set, this script will copy an example in the current directory, to form an initial YML file that you can modify. Can be on of dual_on, dual_off, dual_off_calib, dual_wide_off, dual_wide_on, single_on")

parser.add_argument("--fov", metavar="FOV [mas]", type=float, default=argparse.SUPPRESS,
                    help="field-of-view to show in the plots. Default to 10*fiver_fov")

parser.add_argument("--bg", metavar="PATH", type=str, default=argparse.SUPPRESS,
                    help="path to a image file (jpg, png, etc.) to plot as a background begind the fiber FOV")

parser.add_argument("--bglim", metavar="xleft xright ybottom ytop", type=str, default=argparse.SUPPRESS, nargs=4,
                    help="path to a image file (jpg, png, etc.) to plot as a background begind the fiber FOV")

parser.add_argument("--sc_color", metavar="COLOR", type=str, default="C1",
                    help="color to use to plot the science fiber. Must be a valid Python color string. Default is python C1.")

parser.add_argument("--ft_color", metavar="COLOR", type=str, default="C0",
                    help="color to use to plot the science fiber. Must be a valid Python color string. Default is python C0.")

parser.add_argument("--acq_only", metavar="EMPTY or TRUE/FALSE", type=bool, nargs="?", default=argparse.SUPPRESS, const = True,
                    help="if set, only plot the acquition and not the individual subplots and text info")

parser.add_argument("--demo", metavar="EMPTY or TRUE/FALSE", type=bool, nargs="?", default=argparse.SUPPRESS, const = True,
                    help="if set, send the OBs to the P2 demo server")

parser.add_argument("--nogui", metavar="EMPTY or TRUE/FALSE", type=bool, nargs="?", default=argparse.SUPPRESS, const = True,
                    help="if set, do not plot a visual summary of the OBs before sending to P2, but send them without warning")

parser.add_argument("--dit", metavar="EMPTY or TRUE/FALSE", type=bool, nargs="?", default=argparse.SUPPRESS, const = True,
                    help="if set, just show show the DIT delection figure and exit")

# load arguments into a dictionnary
args = parser.parse_args()
dargs = vars(args) # to treat as a dictionnary

WHEREAMI = os.path.dirname(__file__)

# if DIT keyworg, show image
if "dit" in dargs:
    fig = plt.figure(figsize=(15, 8))
    ax = fig.add_subplot(111)
    ax.imshow(mpimg.imread(WHEREAMI+'/selecting_dit_values.jpg'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    plt.tight_layout()
    plt.show()
    sys.exit()
else:
    if dargs["file"] is None:
        raise Exception("The following arguments are required: file")

# get filename and load yml
filename = dargs["file"]

# is this a "generate" command?
if "generate" in dargs:
    IS_GENERATE = True
    genfile = "{}/examples/{}.yml".format(WHEREAMI, dargs["generate"][0])
    if not(os.path.isfile(genfile)):
        printerr("{} is not an example file. Is {} a valid value for 'generate'?".format(genfile, dargs["generate"]))
    if os.path.isfile(filename):
        printerr("{} already exists, and will not be overwritten.".format(filename))
    else: # copy file
        content = open(genfile, "r").read()
        f = open(filename, "w")
        f.write(content)
        f.close()
    sys.exit()

if not(os.path.isfile(dargs["file"])):
    printerr("{} not found, or is not a file".format(dargs["file"]))

# LOAD CONFIG FILE
loader = yaml.YAML(typ = "rt")
cfg = loader.load(open(filename, "r"))
        
if "fov" in dargs:
    fov = int(dargs["fov"])
else:
    fov = None

if "nogui" in dargs:
    nogui = dargs["nogui"]
else:
    nogui = False

if "demo" in dargs:
    demo = dargs["demo"]
else:
    demo = False

if "acq_only" in dargs:
    acq_only = dargs["acq_only"]
else:
    acq_only = False

if demo:
    # setup for testing on P2 demo server
    api = p2api.ApiConnection('demo', 52052, "tutorial")
else:
    user = input("ESO P2 username: ")
    password = getpass("ESO P2 password: ")
    api = p2api.ApiConnection('production', user, password)

if "bg" in dargs:
    if not("bglim" in dargs):
        printerr("bg keyword (specify a background image) cannot be used without a bglim keyword to specify the limits of the image: Use bglim=[xleft,xright,yleft,yright] in mas")
    if not(os.path.isfile(dargs["bg"])):
        printerr("{} given for bg image not found, or is not a file".format(dargs["bg"]))
    bg = dargs["bg"]
    bglim = dargs["bglim"]
    bglim = [float(dummy) for dummy in bglim.replace("[", "").replace("]", "").replace("(", "").replace(")", "").split(",")]
else:
    bg = None
    bglim = None

FT_COLOR, SC_COLOR = None, None
if "ft_color" in dargs:
    FT_COLOR = dargs["ft_color"]
if "sc_color" in dargs:
    SC_COLOR = dargs["sc_color"]

# Create OB
run_id = cfg["setup"]["run_id"]
folder_name = cfg["setup"]["folder"]
date = cfg["setup"]["date"]
# user friendly
if type(date) != str:
    date = date.isoformat()
    cfg["setup"]["date"] = date

# create the folder if it does not exist
myrun = None
runs, _ = api.getRuns()
for thisrun in runs:
    if thisrun['progId'] == run_id:
        myrun = thisrun
if myrun is None:
    printinf("Available runs are: {}".format([r["progId"] for r in runs]))
    printerr("Run '{}' not found".format(run_id))
folder_info = find_item(folder_name, myrun["containerId"], api, "Folder")
if folder_info is None:
    printinf("Creating folder '{}' in run '{}'".format(folder_name, run_id))
    folder_info, version = api.createFolder(myrun["containerId"], folder_name)
container_id = folder_info["containerId"]

# if concatenation is not none, we need to create a concatenation
concatenation = cfg["setup"]["concatenation"].rstrip().lstrip()
if concatenation.lower() != "none":
    printinf("Creating concatenation '{}' in folder '{}'".format(concatenation, folder_name))
    con, conVersion = api.createConcatenation(container_id, concatenation)
    container_id = con["containerId"]  # new container where to put OBs

# loop through all OBs
for ob_name in cfg["ObservingBlocks"]:
    ob = cfg["ObservingBlocks"][ob_name]
    mode = ob["mode"]
    if mode == "single_on":
        p2ob = p2g.ob.SingleOnOb(ob, cfg["setup"], label = ob_name, iscalib = ob["calib"])
    elif mode == "single_off":
        p2ob = p2g.ob.SingleOffOb(ob, cfg["setup"], label = ob_name)
    elif mode == "dual_on":
        p2ob = p2g.ob.DualOnOb(ob, cfg["setup"], label = ob_name)
    elif mode == "dual_off":
        p2ob = p2g.ob.DualOffOb(ob, cfg["setup"], label = ob_name, iscalib = ob["calib"])
    elif mode == "dual_wide_off":
        p2ob = p2g.ob.DualWideOffOb(ob, cfg["setup"], label = ob_name, iscalib = ob["calib"])
    elif mode == "dual_wide_on":
        p2ob = p2g.ob.DualWideOnOb(ob, cfg["setup"], label = ob_name)
    else:
        printerr("Mode {} is unknown.".format(mode))
    p2ob.generate_templates()
    p2ob.simbad_resolve(ob)
    # in nogui mode, we upload straight to p2
    if nogui:
        p2ob.p2_create(api, container_id)
        p2ob.p2_update(api)
    # in gui mode, we lpot the OB and wait for user input
    else:
        def send_p2(event, fig):
            p2ob.p2_create(api, container_id)
            p2ob.p2_update(api)
            printinf("OB {} sent to run {}".format(ob_name, run_id))
            plt.close(fig)
            return None
        def cancel(event, fig):
            printwar("OB {} was not sent to P2".format(ob_name))
            plt.close(fig)
            return None
        # plot this OB
        fig, gs = plot_ob(p2ob, title = "run: {}        folder: {}\nob: {}        date: {}".format(run_id, folder_name, ob_name, date), fov=fov, bg=bg, bglim=bglim, ft_c = FT_COLOR, sc_c = SC_COLOR, acq_only = acq_only)
        # add buttons:
        axConfirm = fig.add_subplot(gs[0, 4])
        axCancel = fig.add_subplot(gs[0, 5])
        bConfirm = Button(axConfirm, 'Send to P2', color="C2")
        bCancel = Button(axCancel, 'Cancel', color="C3")
        bConfirm.on_clicked(lambda event: send_p2(event, fig))
        bCancel.on_clicked(lambda event: cancel(event, fig))
        plt.show() # wait for the user to confirm sending or cancel

printinf("Done")
