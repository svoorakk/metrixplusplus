#
#    Metrix++, Copyright 2009-2019, Metrix++ Project
#    Link: https://github.com/metrixplusplus/metrixplusplus
#    
#    This file is a part of Metrix++ Tool.
#    

from metrixpp.mpp import api
import re

class Plugin(api.Plugin,
             api.IConfigurable,
             api.Child,
             api.MetricPluginMixin):
    
    def declare_configuration(self, parser):
        self.parser = parser
        parser.add_option("--std.code.assert", "--scass",
            action="store_true", default=False,
            help="Enables collection of number of assert statements in code [default: %default]")

    def configure(self, options):
        self.is_active_assert = options.__dict__['std.code.assert']
        self.pattern_to_search = re.compile(r'\n[^\S\t]*assert[^\S\t]*\(')

    def initialize(self):
        self.declare_metric(self.is_active_assert,
                            self.Field('asserts', int, non_zero=True),
                            self.pattern_to_search,
                            marker_type_mask=api.Marker.T.CODE,
                            region_type_mask=api.Region.T.ANY)

        super(Plugin, self).initialize(fields=self.get_fields(),
            properties=[self.Property('tags', ','.join([]))])
        
        if self.is_active() == True:
            self.subscribe_by_parents_interface(api.ICode)
