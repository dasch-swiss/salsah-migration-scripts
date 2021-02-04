import copy
from pprint import pprint
import requests
import json
from langdetect import detect
from typing import List, Set, Dict, Tuple, Optional

import time


class Converter:

    def __init__(self):
        self.serverpath: str = "https://www.salsah.org"
        # self.serverpath: str = "http://salsahv1.unil.ch"
        self.selection_mapping: Dict[str, str] = {}
        self.selection_node_mapping: Dict[str, str] = {}
        self.hlist_node_mapping: Dict[str, str] = {}
        self.hlist_mapping: Dict[str, str] = {}

        # Retrieving the necessary informations from Webpages.
        self.salsahJson = requests.get(f'{self.serverpath}/api/projects').json()
        self.r = requests.get(
            'https://raw.githubusercontent.com/dhlab-basel/dasch-ark-resolver-data/master/data/shortcodes.csv')
        self.salsahVocabularies = requests.get(f'{self.serverpath}/api/vocabularies').json()

        # Testing stuff
        # self.req = requests.get('https://www.salsah.org/api/resourcetypes/')
        # result = self.req.json()
        # pprint(result)

    # ==================================================================================================================
    # Function that fills the shortname as well as the longname into the empty ontology. Uses https://www.salsah.org/api/projects for that
    def fillShortLongName(self, project):
        tmpOnto["project"]["shortname"] = project["shortname"]
        tmpOnto["project"]["longname"] = project["longname"]

    # ==================================================================================================================
    # Fill in the project id's to the corrisponging projects. Using https://raw.githubusercontent.com/dhlab-basel/dasch-ark-resolver-data/master/data/shortcodes.csv
    def fillId(self, project):
        lines = salsahJson.r.text.split('\n')
        for line in lines:
            parts = line.split(',')
            if len(parts) > 1 and parts[1] == project["shortname"]:
                tmpOnto["project"]["shortcode"] = parts[0]
                # print('Found Knora project shortcode "{}" for "{}"!'.format(shortcode, parts[1]))

    # ==================================================================================================================
    # Fill the description - if present - into the empty ontology
    def fillDesc(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["description"] and vocabularies["shortname"].lower() == project["shortname"].lower():
                tmpOnto["project"]["descriptions"] = vocabularies["description"]

    # ==================================================================================================================
    # Fill in the vocabulary name and label
    def fillVocName(self, projects):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:
                tmpOnto["project"]["ontologies"][0]["name"] = vocabularies["shortname"]
                tmpOnto["project"]["ontologies"][0]["label"] = vocabularies["longname"]

    # ==================================================================================================================
    # Function responsible to get the keywords of the corresponding project
    def fetchKeywords(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:

                req = requests.get(f'{self.serverpath}/api/projects/{vocabularies["shortname"]}?lang=all')

                result = req.json()
                if 'project_info' in result.keys():
                    project_info = result['project_info']
                    if "keywords" in project_info:  # This is needed for DYLAN since not all have a keyword TODO: check if that is correct
                        if project_info['keywords'] is not None:
                            tmpOnto["project"]["keywords"] = list(
                                map(lambda a: a.strip(), project_info['keywords'].split(',')))
                        else:
                            tmpOnto["project"]["keywords"] = [result['project_info']['shortname']]
                else:
                    continue

    # ==================================================================================================================
    # Function that fetches the lists for a correspinding project
    def fetchLists(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:
                payload: dict = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/selections/', params=payload)
                result = req.json()

                selections = result['selections']

                # Let's make an empty list for the lists:
                selections_container = []

                for selection in selections:
                    self.selection_mapping[selection['id']] = selection['name']
                    root = {
                        'name': selection['name'],
                        'labels': dict(map(lambda a: (a['shortname'], a['label']), selection['label']))
                    }
                    if selection.get('description') is not None:
                        root['comments'] = dict(
                            map(lambda a: (a['shortname'], a['description']), selection['description']))
                    payload = {'lang': 'all'}
                    req_nodes = requests.get(f'{self.serverpath}/api/selections/' + selection['id'], params=payload)
                    result_nodes = req_nodes.json()

                    self.selection_node_mapping.update(
                        dict(map(lambda a: (a['id'], a['name']), result_nodes['selection'])))
                    root['nodes'] = list(map(lambda a: {
                        'name': 'S_' + a['id'],
                        'labels': a['label']
                    }, result_nodes['selection']))
                    selections_container.append(root)

                    # pprint(selections_container)
                    # time.sleep(15)

                #
                # now we get the hierarchical lists (hlists)
                #
                payload = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/hlists', params=payload)
                result = req.json()

                self.hlist_node_mapping.update(dict(map(lambda a: (a['id'], a['name']), result['hlists'])))

                hlists = result['hlists']

                # pprint(selections_container)
                # time.sleep(15)

                #
                # this is a helper function for easy recursion
                #
                def process_children(children: list) -> list:
                    newnodes = []
                    for node in children:
                        self.hlist_node_mapping[node['id']] = node['name']
                        newnode = {
                            'name': 'H_' + node['id'],
                            'labels': dict(map(lambda a: (a['shortname'], a['label']), node['label']))
                        }
                        if node.get('children') is not None:
                            newnode['nodes'] = process_children(node['children'])
                        newnodes.append(newnode)
                    return newnodes

                for hlist in hlists:
                    root = {
                        'name': hlist['name'],
                        'labels': dict(map(lambda a: (a['shortname'], a['label']), hlist['label']))
                    }
                    self.hlist_mapping[hlist['id']] = hlist['name']
                    if hlist.get('description') is not None:
                        root['comments'] = dict(
                            map(lambda a: (a['shortname'], a['description']), hlist['description']))
                    payload = {'lang': 'all'}
                    req_nodes = requests.get(f'{self.serverpath}/api/hlists/' + hlist['id'], params=payload)
                    result_nodes = req_nodes.json()

                    root['nodes'] = process_children(result_nodes['hlist'])
                    selections_container.append(root)

                tmpOnto["project"]["lists"] = selections_container
                # pprint(selections_container)
                # pprint('==================================================================================================================')
                # pprint('==================================================================================================================')

    # ==================================================================================================================
    # Function that fetches all the resources that correspond to a vocabulary/ontology
    def fetchResources(self, project):

        superMap = {
            "movie": "MovingImageRepresentation",
            "object": "Resource",
            "image": "StillImageRepresentation"
        }

        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if project["id"] == vocabularies["project_id"]:
                payload: dict = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/resourcetypes/', params=payload)
                resourcetypes = req.json()

                # Here we type in the "name"
                for momResId in resourcetypes["resourcetypes"]:
                    tmpOnto["project"]["ontologies"][0]["resources"].append({
                        "name": momResId["label"][0]["label"],
                        "super": "",
                        "labels": {},
                        "cardinalities": []
                    })
                    # Here we fill in the labels
                    for label in momResId["label"]:
                        tmpOnto["project"]["ontologies"][0]["resources"][-1]["labels"].update(
                            {label["shortname"]: label["label"]})
                    # Here we fill in the cardinalities
                    req = requests.get(f'{self.serverpath}/api/resourcetypes/{momResId["id"]}?lang=all')
                    resType = req.json()
                    resTypeInfo = resType["restype_info"]

                    # if resTypeInfo["class"] not in superMap: #  here we fill in our superMap
                    #     pprint(resTypeInfo["class"])
                    #     exit()

                    tmpOnto["project"]["ontologies"][0]["resources"][-1]["super"] = superMap[
                        resTypeInfo["class"]]  # Fill in the super of the ressource

                    for propertyId in resTypeInfo["properties"]:
                        tmpOnto["project"]["ontologies"][0]["resources"][-1]["cardinalities"].append({
                            "propname": propertyId["name"],
                            # "gui_order": "",  # TODO gui_order not yet implemented by knora.
                            "cardinality": str(propertyId["occurrence"])
                        })
            else:
                continue

    # ==================================================================================================================
    # The following functions are helper functions for "fetchProperties"
    # ==================================================================================================================
    # Function that returns all the resource id's of a project.
    # It gets the json file of the resources of the current project as parameter.
    def res_ids(self, resource_types_json):
        project_resources_ids = []

        for resource_type_id in resource_types_json["resourcetypes"]:
            project_resources_ids.append(resource_type_id["id"])

        return project_resources_ids

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a List of all the properties id's that are used in that project
    # It gets the json file of the resources of the current project as parameter.
    def prop_ids(self, resource_types_json):
        all_project_properties_ids = []

        for resource_type_id in resource_types_json["resourcetypes"]:
            for property in resource_type_id:
                if property["id"] not in all_project_properties_ids:
                    all_project_properties_ids.append(property["id"])
                else:
                    continue

        return all_project_properties_ids

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns the json of a given property-id. Used in almost all the subsequent functions as parameter
    # Gets the id of the property as parameter
    def prop_json(self, prop_id):
        req = requests.get(f'{self.serverpath}/api/resourcetypes/{prop_id}?lang=all')
        prop_info = req.json()
        return prop_info

    # ==================================================================================================================
    # Function that Returns the Name of the property
    # Gets the json of the property and the property id as parameter
    def prop_name(self, prop_id, prop_json):
        prop_name = ""

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                prop_name = properties["name"]

        return prop_name

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns the super of the property
    # Gets the json of the property, the property id and the supermap and objectmap as parameter
    def prop_super(self, prop_id, prop_json, super_map, object_map):

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                if properties["vt_name"] is not super_map:
                    return "hasValue"
                else:
                    return super_map[object_map[properties["vt_name"]]]


    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns the object of the property
    # Gets the json of the property, the property id and the supermap as parameter
    def prop_object(self, prop_id, prop_json, object_map):

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                return object_map[properties["vt_name"]]


    # -------------------------------------------------------------------------------------------------------------------
    # Function that returns a list of dicts with all the <language: Label> of the property. Each label occurs only once
    # Gets the json of the property and the property id as parameter
    def prop_labels(self, prop_id, prop_json):
        label_list = []

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                tmp_dict = {}

                for labels in properties["label"]:
                    tmp_dict.update({
                        labels["shortname"]: labels["label"]
                    })
                    if tmp_dict not in label_list:
                        label_list.append()

        return label_list

    # -------------------------------------------------------------------------------------------------------------------
    # Function that returns a list with all comments of the property
    # Gets the json of the property and the property id as parameter
    def prop_comments(self, prop_id, prop_json):
        comments_list = []

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                tmp_dict = {}

                for descriptions in properties["description"]:
                    tmp_dict.update({
                        descriptions["shortname"]: descriptions["description"]
                    })
                    if tmp_dict not in comments_list:
                        comments_list.append()

        return comments_list

    # -------------------------------------------------------------------------------------------------------------------
    # Function that returns the gui_element of the property
    # Gets the json of the property, the property id and the gui_element_map as parameter
    def prop_gui_element(self, prop_id, prop_json, gui_element_map):

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:
                return gui_element_map[properties["gui_name"]]

    # -------------------------------------------------------------------------------------------------------------------
    # Function that returns a dict of the gui_attributes of the property
    # Gets the json of the property and the property id as parameter
    def prop_gui_attributes(self, prop_id, prop_json):
        attributes_dict = {}

        for properties in prop_json["restype_info"]["properties"]:
            if properties["id"] == prop_id:

                attribute_type = ""
                attribute_value = 0

                attribute_string = properties["attributes"] #  A attributes_string might look like "size=60;maxlength=200"

                comma_split = attribute_string.split(";") #  comma_split looks eg like: ["size"= 60, "maxlength"= 200]
                for sub_splits in comma_split:
                    attribute_type, attribute_value = sub_splits.split("=")

                    attributes_dict.update({
                        attribute_type: attribute_value
                    })

        return attributes_dict

    # ==================================================================================================================
    def fetchProperties(self, project):
        controlList = []  # List to identify dublicates of properties. We dont want dublicates in the properties list
        propId = 0  # Is needed to save the property Id to get the guiElement
        resId = 0  # Is needed to save the resource Id to get the guiElement

        guiEleMap = {
            "text": "SimpleText",
            "textarea": "Textarea",
            "richtext": "Richtext",
            "": "Colorpicker",
            "date": "Date",
            "": "Slider",
            "geoname": "Geonames",
            "spinbox": "Spinbox",
            "": "Checkbox",
            "radio": "Radio",
            "": "List",
            "pulldown": "Pulldown",
            "hlist": "Pulldown",
            "searchbox": "Searchbox",
            "interval": "IntervalValue",
            "fileupload": "__FILEUPLOAD__"

        }  # Dict that maps the old guiname from salsa to the new guielement from knorapy

        objectMap = {
            "Text": "TextValue",
            "Richtext": "TextValue",
            "Iconclass": "TextValue",
            "": "ColorValue",
            "Date": "DateValue",
            "Time": "TimeValue",
            "Floating point number": "DecimalValue",
            "": "GeomValue",
            "Geoname": "GeonameValue",
            "Integer value": "IntValue",
            "": "BooleanValue",
            "": "UriValue",
            "": "IntervalValue",
            "Selection": "ListValue",
            "Hierarchical list": "ListValue",
            "Resource pointer": "LinkValue"
        }  # Dict that maps the old vt-name from salsa to the new Object type from knorapy
        # TODO right mapping from object map to super map
        superMap = {
            "": "hasValue",
            "LinkValue": "hasLinkTo",
            "ColorValue": "hasColor",
            "": "hasComment",
            "": "hasGeometry",
            "": "isPartOf",
            "": "isRegionOf",
            "": "isAnnotationOf",
            "": "seqnum"
        }  # Dict that maps the old the super corresponding to the object-type

        #-----------------------------------------------------------------------------------
        # Getting framework for the Properties section of the ontology
        tmpOnto["project"]["ontologies"][0]["properties"].append({
            "name": "",
            "super": [],
            "object": "",
            "labels": {},
            "comments": {},
            "gui_element": "",
            "gui_attributes": {}
        })
        #-----------------------------------------------------------------------------------


        # TODO: ----------------------------Assembly-------------------------------------
        #
        # hlist_node_mapping = {}
        #
        # req = requests.get(f'{self.serverpath}/api/selections/')
        # result = req.json()
        # selections = result["selections"]
        #
        # req2 = requests.get(f'{self.serverpath}/api/hlists/')
        # result2 = req2.json()
        # hlists = result2["hlists"]
        #
        # for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
        #     if project["id"] == vocabularies["project_id"]:



        # TODO: ----------------------------Assembly-------------------------------------

    # ==================================================================================================================


if __name__ == '__main__':

    # This is a "blank" ontology. the json file is in the form we need in the new knora
    emptyOnto = {
        "prefixes": {},
        "project": {
            "shortcode": "",
            "shortname": "",
            "longname": "",
            "descriptions": {},
            "keywords": [],
            "lists": [],
            "groups": [],
            "users": [],
            "ontologies": [{
                "name": "",
                "label": "",
                "properties": [],
                "resources": []
            }]
        }
    }

    # Create an empty ontology
    tmpOnto = copy.deepcopy(emptyOnto)

    # Creating the ontology object. This object will create the new jsons.
    salsahJson = Converter()

    # Here the ontology object is being filled
    for projects in salsahJson.salsahJson["projects"]:
        # pprint("Making Deepcopy")
        tmpOnto = copy.deepcopy(
            emptyOnto)  # Its necessary to reset the tmpOnto for each project. Otherwhise they will overlap
        # pprint("FillShortLongName")
        salsahJson.fillShortLongName(projects)  # Fill the shortname as well as the longname into the empty ontology.
        # pprint("FillID")
        salsahJson.fillId(projects)  # Fill in the project id's (shortcode) to the corresponding projects.
        # pprint("FillDesc")
        salsahJson.fillDesc(projects)  # Fill in the vocabulary name and label
        # pprint("FillVocName")
        salsahJson.fillVocName(projects)  # Fill in the vocabulary name and label
        salsahJson.fetchKeywords(projects)  # Fills in the keywords of the corresponding project
        salsahJson.fetchLists(projects)
        # pprint("FetchRessources")
        salsahJson.fetchResources(projects)
        # pprint("FetchProperties")
        salsahJson.fetchProperties(projects)
        # Creating the new json files
        f = open("KAPPA" + projects["longname"] + ".json", 'w')
        f.write(json.dumps(tmpOnto, indent=4))
