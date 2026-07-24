def add_ncrystal_union_material(instrument, name, cfgstr, split=False):
    try:
        import NCrystal.mcstasutils as NCms
    except ImportError or ModuleNotFoundError:
        raise RuntimeError("Install NCrystal to use this feature in McStasScript.")

    abs_info, ncrystal_processes = NCms.cfgstr_2_unioncfg(cfgstr=cfgstr, split_by_physics=split)

    process_names = []
    for process in ncrystal_processes:
        process_name = name + "_" + process[1]
        process_names.append(process_name)
        comp = instrument.add_component(process_name, "NCrystal_process")
        comp.cfg = '"' + process[0] + '"'

    comp = instrument.add_component(name, "Union_make_material")
    comp.my_absorption = abs_info
    comp.process_string = '"' + ",".join(process_names) + '"'
