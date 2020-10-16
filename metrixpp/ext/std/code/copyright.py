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
        parser.add_option("--std.general.copyright", "--sgcr",
            action="store_true", default=False,
            help="Enables collection of flag to indicate if a code file has a copyright header [default: %default]")
        parser.add_option("--std.general.copyright.tags", "--sgcrt", type=str,
            default=" ",
            help="A list of copyright holders to search, separated by comma [default: %default]")


    def configure(self, options):
        self.is_active_copyright = options.__dict__['std.general.copyright']
        self.cr_tags_list = options.__dict__['std.general.copyright.tags'].split(',')
        self.cr_tags_list.sort()
        for tag in self.cr_tags_list:
            if re.match(r'''^[A-Za-z0-9_ ]+$''', tag) == None:
                self.parser.error('option --std.general.copyright.tags: tag {0} includes not allowed symbols'.
                                  format(tag))
        if len(self.cr_tags_list) == 0:
            self.cr_tags_list = [' ']
        self.pattern_to_search = re.compile(
            r'^/[/|*].*copyright.*({0}).*$'.
            format('|'.join(self.cr_tags_list)), flags = re.IGNORECASE | re.MULTILINE)
        print(self.pattern_to_search)
        print(r'^/[/|*].*copyright.*({0}).*$'.format('|'.join(self.cr_tags_list)))
    def initialize(self):
        self.declare_metric(self.is_active_copyright,
                            self.Field('copyright', int, non_zero=True),
                            self.pattern_to_search,
                            marker_type_mask=api.Marker.T.COMMENT,
                            region_type_mask=api.Region.T.GLOBAL)

        super(Plugin, self).initialize(fields=self.get_fields(),
            properties=[self.Property('tags', ','.join([]))])
        
        if self.is_active() == True:
            self.subscribe_by_parents_interface(api.ICode)
