#coding: utf8
"""Define a class to contain a GRAVITY observing block.

An object of this class will have a p2_create and p2_update method to create or update itself on the P2 server.
"""

# import the template and common functions of this package
from .. import common
from .. import tpl

# we need astroquery to get magnitudes, coordinates, etc.
from astroquery.simbad import Simbad
from astropy import units as u
from astropy.coordinates import SkyCoord

# to define abstract method
from abc import ABC, abstractmethod

# add some votable fields to get the magnitudes, proper motion, and plx required in acq template
Simbad.add_votable_fields('flux(V)')
Simbad.add_votable_fields('flux(K)')
Simbad.add_votable_fields('flux(H)')
Simbad.add_votable_fields('flux(R)')
Simbad.add_votable_fields('pmdec')
Simbad.add_votable_fields('pmra')
Simbad.add_votable_fields('plx')


class ObservingBlock(object):
    def __init__(self, yml, setup, label = ""):
        """
        @param yml: dict containing all the info loaded from the YML of this OB
        @param setup: dict containing all the info loaded from the setup part of the YML
        @param label: a label for the OB (as it will appear in P2)
        """
        self.label = label
        self.setup = setup
        self.yml = yml
        self.objects = yml["objects"]        
        self.acquisition = None
        self.templates = []
        self.ob = None
        self.target = dict({})
        self.ob_type = "ObservingBlock"
        return None
    
    def _populate_from_simbad(self, target_table, target_name = ""):
        """
        Populate the self.target attribute using the data available in the target_table retrieved from
        Simbad. Target_name is only used to display useful warning and error to the user.
        Populate: RA, DEC, PMRA, PMDEC from simbad.
        """
        coord = SkyCoord(target_table["RA"][0], target_table['DEC'][0], unit=(u.hourangle, u.deg))
        self.target["ra"] = coord.ra.to_string(unit=u.hourangle, sep=":", precision=3, pad=True)
        self.target["dec"] = coord.dec.to_string(sep=":", precision=3, alwayssign=True)
        try:
            self.target["properMotionRa"] = round((target_table["PMRA"].to(u.arcsec/u.yr))[0].value, 5)
            self.target["properMotionDec"] = round((target_table["PMDEC"].to(u.arcsec/u.yr))[0].value, 5)
        except:
            common.printwar("Proper motion not found on Simbad for target {}".format(target_name))
        return None

    def populate_from_yml(self, yml):
        """
        This can be used to add additional elements in the OB from the yml itself (instead of from Simbad resolution)
        This will be overwritten in daughter classes to add additional parameters. 
        """
        self.ob["obsDescription"]["userComments"] = "Generated by p2Gravity script v0.0"        
        if "description" in yml:
            self.ob["obsDescription"]["name"] = yml["description"]
        if "constraints" in yml:
            for key in yml["constraints"]:
                self.ob["constraints"][key] = yml["constraints"][key]
        return None
    
    def simbad_resolve(self, ob):
        """
        Search the information of the star from Simbad.
        """
        target_name = ob["target"]
        common.printinf("Resolving target {} on Simbad".format(target_name))
        target_table = Simbad.query_object(target_name)
        if target_table is None:
            raise ValueError('Input not known by Simbad')
        common.printinf("Simbad resolution of {}: \n {}".format(target_name, target_table))
        if len(target_table) > 1:
            printwar("There are multiple results from Simbad. Which one should I use? (1, 2, etc.?)")
            stop()
        self.target = dict({})
        self.target["name"] = target_name        
        self.acquisition.populate_from_simbad(target_table, target_name = target_name)
        self._populate_from_simbad(target_table, target_name = target_name)        
        return None

    @abstractmethod
    def generate_templates(self):
        raise NotImplementedError("Must be overriden")

    def p2_create(self, api, container_id):
        """
        Create the OB on P2.
        @param api: the p2 api object to send data to p2 (must be initialized beforehand)
        @param container_id: id of the container where to put the OB
        """
        common.printinf("Creating OB '{}'".format(self.label))        
        ob, version = api.createOB(container_id, self.label)
        self.ob_id = ob["obId"]
        self.version = version
        self.ob = ob
        # create templates
        common.printinf("Creating templates for OB '{}'".format(self.label))
        self.acquisition.p2_create(api, self.ob_id)
        for template in self.templates:
            template.p2_create(api, self.ob_id)        
        return None

    def p2_update(self, api):
        """
        Update info of the OB on P2
        """
        common.printinf("Updating OB '{}'".format(self.label))
        for key in self.target:
            self.ob["target"][key] = self.target[key]
        # YML explicit stuff have priority over the auto generated values
        self.populate_from_yml(self.setup)
        self.populate_from_yml(self.yml)
        # save updated OB
        api.saveOB(self.ob, self.version)
        common.printinf("Updating templates in run OB '{}'".format(self.label))
        self.acquisition.p2_update(api)
        for template in self.templates:
            template.p2_update(api)
        return None
    

