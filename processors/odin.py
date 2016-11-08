#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .utils import post_json
from .ds import Document
import re
import json


class Interval(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def to_JSON_dict(self):
        return {"start":self.start, "end":self.end}

    def to_JSON(self):
        return json.dumps(self.to_JSON_dict(), sort_keys=True, indent=4)

    @staticmethod
    def load_from_JSON(json):
        return Interval(start=json["start"], end=json["end"])

class Mention(object):

    TBM = "TextBoundMention"
    EM = "EventMention"
    RM = "RelationMention"

    def __init__(self,
                token_interval,
                sentence,
                document,
                foundBy,
                label,
                labels=None,
                trigger=None,
                arguments=None,
                paths=None,
                keep=True,
                doc_id=None):

        self.label = label
        self.labels = labels if labels else [self.label]
        self.tokenInterval = token_interval
        self.start = self.tokenInterval.start
        self.end = self.tokenInterval.end
        self.document = document
        self._doc_id = doc_id or hash(self.document)
        self.sentence = sentence
        if trigger:
            # NOTE: doc id is not stored for trigger's json,
            # as it is assumed to be contained in the same document as its parent
            trigger.update({"document": self._doc_id})
            self.trigger = Mention.load_from_JSON(trigger, self._to_document_map())
        else:
            self.trigger = None
        # unpack args
        self.arguments = {role:[Mention.load_from_JSON(a, self._to_document_map()) for a in args] for (role, args) in arguments.items()} if arguments else None
        self.paths = paths
        self.keep = keep
        self.foundBy = foundBy
        # other
        self.sentenceObj = self.document.sentences[self.sentence]
        self.text = " ".join(self.sentenceObj.words[self.start:self.end])
        # recover offsets
        self.characterStartOffset = self.sentenceObj.startOffsets[self.tokenInterval.start]
        self.characterEndOffset = self.sentenceObj.endOffsets[self.tokenInterval.end]
        # for later recovery
        self.id = None
        self.type = self._set_type()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.text

    def to_JSON_dict(self):
        m = dict()
        m["id"] = self.id
        m["type"] = self.type
        m["label"] = self.label
        m["labels"] = self.labels
        m["tokenInterval"] = self.tokenInterval.to_JSON_dict()
        m["characterStartOffset"] = self.characterStartOffset
        m["characterEndOffset"] = self.characterEndOffset
        m["sentence"] = self.sentence
        m["document"] = self._doc_id
        # do we have a trigger?
        if self.trigger:
             m["trigger"] = self.trigger.to_JSON_dict()
        # do we have arguments?
        if self.arguments:
            m["arguments"] = self._arguments_to_JSON_dict()
        # handle paths
        if self.paths:
            m["paths"] = self.paths
        m["keep"] = self.keep
        m["foundBy"] = self.foundBy
        return m

    def to_JSON(self):
        return json.dumps(self.to_JSON_dict(), sort_keys=True, indent=4)

    def _arguments_to_JSON_dict(self):
        return dict((role, [a.to_JSON_dict() for a in args]) for (role, args) in self.arguments.items())

    def _paths_to_JSON_dict(self):
        return {role: paths.to_JSON_dict() for (role, paths) in self.paths}

    @staticmethod
    def load_from_JSON(mjson, docs_dict):
        # recover document
        doc_id = mjson["document"]
        doc = docs_dict[doc_id]
        labels = mjson["labels"]
        kwargs = {
            "label": mjson.get("label", labels[0]),
            "labels": labels,
            "token_interval": Interval.load_from_JSON(mjson["tokenInterval"]),
            "sentence": mjson["sentence"],
            "document": doc,
            "doc_id": doc_id,
            "trigger": mjson.get("trigger", None),
            "arguments": mjson.get("arguments", None),
            "paths": mjson.get("paths", None),
            "keep": mjson.get("keep", True),
            "foundBy": mjson["foundBy"]
        }
        m = Mention(**kwargs)
        # set IDs
        m.id = mjson["id"]
        m._doc_id = doc_id
        # set character offsets
        m.character_start_offset = mjson["characterStartOffset"]
        m.character_end_offset = mjson["characterEndOffset"]
        return m

    def _to_document_map(self):
        return {self._doc_id: self.document}

    def _set_type(self):
        # event mention
        if self.trigger != None:
            return Mention.EM
        # textbound mention
        elif self.trigger == None and self.arguments == None:
            return Mention.TBM
        else:
            return Mention.RM
