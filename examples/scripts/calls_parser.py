import idaapi, idc
from herapi import *

def get_unique_name(name_candidate):
	if idc.get_name_ea_simple(name_candidate) == idaapi.BADADDR:
		return name_candidate

	i = 0
	while idc.get_name_ea_simple(name_candidate + '_' + str(i)) != idaapi.BADADDR:
		i += 1
	return name_candidate + '_' + str(i)

class CallsParser(Scheme):
	def __init__(self, *function_address):
		if len(function_address) == 0:
			raise ValueError("No function address provided")

		obj_pat = MultiObjectPat(*function_address)
		pattern = CallPat(obj_pat, ObjPat(), RefPat(ObjPat()), skip_missing=True)
		super().__init__(pattern)

	def on_matched_item(self, item, ctx: PatternContext) -> bool:
		arg0 = item.a[0]
		arg1 = item.a[1]
		new_name = idc.get_strlit_contents(arg0.obj_ea)
		if new_name is None: return False
		new_name = new_name.decode()
		new_name = get_unique_name(new_name)
		rename_address = arg1.x.obj_ea
		print("renaming", hex(rename_address), "to", new_name)
		idaapi.set_name(rename_address, new_name)
		return False

def find_calls(*functions):
	scheme = CallsParser(*functions)
	matcher = Matcher(scheme)
	matcher.match_objects_xrefs(*functions)