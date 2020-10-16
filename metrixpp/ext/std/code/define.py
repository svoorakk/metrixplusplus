#
#    Metrix++, Copyright 2020, Sridhar Voorakkara
#    Link: https://github.com/svoorakk/metrixplusplus
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
        parser.add_option("--std.code.define", "--scdef",
            action="store_true", default=False,
            help="Enables collection of number of #define statements in code [default: %default]")

    def configure(self, options):
        self.is_active_define = options.__dict__['std.code.define']
        self.pattern_to_search = re.compile(r'#define')

    def initialize(self):
        self.declare_metric(self.is_active_define,
                            self.Field('defines', int, non_zero=True),
                            self.pattern_to_search,
                            marker_type_mask=api.Marker.T.PREPROCESSOR,
                            region_type_mask=api.Region.T.ANY)

        super(Plugin, self).initialize(fields=self.get_fields())
        
        if self.is_active() == True:
            self.subscribe_by_parents_interface(api.ICode)
