import copy
from pprint import pprint
import requests
import json
from langdetect import detect
from typing import List, Set, Dict, Tuple, Optional

import time


class Converter:

    def __init__(self):
        self.selection_mapping: Dict[str, str] = {}
        self.selection_node_mapping: Dict[str, str] = {}
        self.hlist_node_mapping: Dict[str, str] = {}
        self.hlist_mapping: Dict[str, str] = {}


        # Retrieving the necessary informations from Webpages.
        self.salsahJson = requests.get('https://www.salsah.org/api/projects').json()
        self.r = requests.get(
            'https://raw.githubusercontent.com/dhlab-basel/dasch-ark-resolver-data/master/data/shortcodes.csv')
        self.salsahVocabularies = requests.get('https://www.salsah.org/api/vocabularies').json()

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

                req = requests.get('https://www.salsah.org/api/projects/{}?lang=all'.format(vocabularies["shortname"]))

                result = req.json()
                if 'project_info' in result.keys():
                    project_info = result['project_info']
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
                req = requests.get('http://salsah.org/api/selections/', params=payload)
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
                    req_nodes = requests.get('http://salsah.org/api/selections/' + selection['id'], params=payload)
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
                req = requests.get('http://salsah.org/api/hlists', params=payload)
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
                    req_nodes = requests.get('http://salsah.org/api/hlists/' + hlist['id'], params=payload)
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
                req = requests.get('http://salsah.org/api/resourcetypes/', params=payload)
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
                    req = requests.get('https://salsah.org/api/resourcetypes/{}?lang=all'.format(momResId["id"]))
                    resType = req.json()
                    resTypeInfo = resType["restype_info"]

                    # if resTypeInfo["class"] not in superMap: #  here we fill in our superMap
                    #     pprint(resTypeInfo["class"])
                    #     exit()

                    tmpOnto["project"]["ontologies"][0]["resources"][-1]["super"] = superMap[resTypeInfo["class"]] # Fill in the super of the ressource



                    for propertyId in resTypeInfo["properties"]:
                        tmpOnto["project"]["ontologies"][0]["resources"][-1]["cardinalities"].append({
                            "propname": propertyId["name"],
                            # "gui_order": "",  # TODO gui_order not yet implemented by knora.
                            "comments": {},
                            "cardinality": propertyId["occurrence"]
                        })
                        # Fill in the descriptions
                        if propertyId["description"] is not None and isinstance(propertyId["description"], list):
                            for descriptionId in propertyId["description"]:
                                tmpOnto["project"]["ontologies"][0]["resources"][-1]["cardinalities"][-1][
                                    "comments"].update({
                                    detect(descriptionId["description"]): descriptionId["description"]
                                })
            else:
                continue

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

        hlist_node_mapping = {}

        req = requests.get('http://salsah.org/api/selections/')
        result = req.json()
        selections = result["selections"]

        req2 = requests.get('http://salsah.org/api/hlists/')
        result2 = req2.json()
        hlists = result2["hlists"]


        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if project["id"] == vocabularies["project_id"]:
                payload: dict = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get('http://salsah.org/api/resourcetypes/', params=payload)
                resourcetypes = req.json()

                controlList.clear()  # The list needs to be cleared for every project

                for momResId in resourcetypes["resourcetypes"]:
                    for propertiesId in momResId["properties"]:
                        # for labelId in propertiesId["label"]: - If you want for every language a single property
                        if propertiesId["label"][0]["label"] in controlList:
                            continue
                        else:
                            # Fill in the name of the property as well as getting the framework done
                            tmpOnto["project"]["ontologies"][0]["properties"].append({
                                "name": "",
                                "super": "",
                                "object": "",
                                "labels": {},
                                "gui_element": "",
                                "gui_attributes": {}
                            })
                            tmpOnto["project"]["ontologies"][0]["properties"][-1]["name"] = propertiesId["label"][0]["label"]
                            controlList.append(propertiesId["label"][0]["label"])

                            # Fill in the labels of the properties - Its all the different language-names of the property
                            for labelId in propertiesId["label"]:
                                tmpOnto["project"]["ontologies"][0]["properties"][-1]["labels"].update({
                                    labelId["shortname"]: labelId["label"]
                                })
                        # finding property name plus its id in order to fill in guiname
                        for labelId in propertiesId["label"]:
                            if labelId["label"] == tmpOnto["project"]["ontologies"][0]["properties"][-1]["name"]:
                                propId = propertiesId["id"]

                        req = requests.get(
                            'https://salsah.org/api/resourcetypes/{}?lang=all'.format(momResId["id"]))
                        resType = req.json()
                        resTypeInfo = resType["restype_info"]

                        for property in resTypeInfo["properties"]:
                            if "id" in property and property["id"] == propId:
                                tmpOnto["project"]["ontologies"][0]["properties"][-1]["gui_element"] = guiEleMap[property["gui_name"]] # fill in gui_element
                                if "attributes" in property and property["attributes"] != "" and property["attributes"] is not None:  # fill in all gui_attributes
                                    finalSplit = []
                                    tmpstr = property["attributes"]
                                    firstSplit = tmpstr.split(";")
                                    for splits in firstSplit:
                                        finalSplit.append(splits.split("="))


                                    for numEle in range(len(finalSplit)): #  instead of the list id, insert the name of the list via the id .replace("selection", "hlist")

                                        if (finalSplit[numEle][0] == "selection" or finalSplit[numEle][0] == "hlist"):  # here the selections-id's are comvertet into the name
                                            for selectionId in selections:
                                                if finalSplit[numEle][1] == selectionId["id"] and selectionId["name"] != "":
                                                    finalSplit[numEle][1] = selectionId["name"]

                                            for hlistsId in hlists:
                                                if finalSplit[numEle][1] == hlistsId["id"] and hlistsId["name"] != "":
                                                    finalSplit[numEle][1] = hlistsId["name"]

                                            finalSplit[numEle][0] = "hlist"

                                    for numEle in range(len(finalSplit)):
                                        tmpOnto["project"]["ontologies"][0]["properties"][-1]["gui_attributes"].update({
                                            finalSplit[numEle][0]: finalSplit[numEle][1]
                                        })
                                tmpOnto["project"]["ontologies"][0]["properties"][-1]["object"] = objectMap[property["vt_name"]]  # fill in object

                                if objectMap[property["vt_name"]] is not superMap:  # fill in the super of the property. Default is "hasValue"
                                    tmpOnto["project"]["ontologies"][0]["properties"][-1]["super"] = "hasValue"
                                else:
                                    tmpOnto["project"]["ontologies"][0]["properties"][-1]["super"] = superMap[objectMap[property["vt_name"]]]


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
        #pprint("Making Deepcopy")
        tmpOnto = copy.deepcopy(
            emptyOnto)  # Its necessary to reset the tmpOnto for each project. Otherwhise they will overlap
        #pprint("FillShortLongName")
        salsahJson.fillShortLongName(projects)  # Fill the shortname as well as the longname into the empty ontology.
        #pprint("FillID")
        salsahJson.fillId(projects)  # Fill in the project id's (shortcode) to the corresponding projects.
        #pprint("FillDesc")
        salsahJson.fillDesc(projects)  # Fill in the vocabulary name and label
        #pprint("FillVocName")
        salsahJson.fillVocName(projects)  # Fill in the vocabulary name and label
        salsahJson.fetchKeywords(projects) #  Fills in the keywords of the corresponding project
        salsahJson.fetchLists(projects)
        #pprint("FetchRessources")
        salsahJson.fetchResources(projects)
        #pprint("FetchProperties")
        salsahJson.fetchProperties(projects)
        # Creating the new json files
        f = open(projects["longname"] + ".json", 'w')
        f.write(json.dumps(tmpOnto, indent=4))
