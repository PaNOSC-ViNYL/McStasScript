import mcstasscript as ms

def create_data(path):
    instrument = ms.McStas_instr("laue_example", output_path=path)
    
    source = instrument.add_component("source", "Source_simple")
    source.set_parameters(xwidth=0.01, yheight=0.01,
                          dist=5, focus_xw=0.01, focus_yh=0.01)
    source.lambda0 = instrument.add_parameter("wavelength", value=3.0)
    source.dlambda = "0.95*wavelength"

    sample = instrument.add_component("sample", "Single_crystal")
    sample.set_parameters(radius=source.focus_xw, yheight=source.focus_yh,
                          reflections='"YBaCuO.lau"', mosaic=30)
    sample.set_AT(source.dist, RELATIVE=source)
    sample.set_ROTATED([8, 4, 0])
                      
    mon = instrument.add_component("PSD", "PSD_monitor")
    mon.set_AT(source.dist + 0.1, RELATIVE=source)
    mon.set_parameters(nx=300, ny=300, filename='"psd.dat"',
                       xwidth=1.0, yheight=1.0,
                       restore_neutron=1)
                       
    lmon = instrument.add_component("div_lambda_h", "DivLambda_monitor")
    lmon.set_AT(0, RELATIVE=mon)
    lmon.set_parameters(nL=100, nh=70, maxdiv_h=80, filename='"div_lambda_h.dat"',
                        Lmin="0.05*wavelength", Lmax="1.95*wavelength",
                        xwidth=mon.xwidth, yheight=mon.yheight,
                        restore_neutron=1)
                        
    lmon = instrument.add_component("div_lambda_v", "DivLambda_monitor")
    lmon.set_AT(0, RELATIVE=mon)
    lmon.set_ROTATED([0, 0, 90], RELATIVE=mon)
    lmon.set_parameters(nL=100, nh=70, maxdiv_h=80, filename='"div_lambda_v.dat"',
                        Lmin="0.05*wavelength", Lmax="1.95*wavelength",
                        xwidth=mon.xwidth, yheight=mon.yheight,
                        restore_neutron=1)
                        
    lmon = instrument.add_component("lambda", "L_monitor")
    lmon.set_AT(0, RELATIVE=mon)
    lmon.set_parameters(nL=300, filename='"lambda_transmission.dat"',
                        Lmin="0.05*wavelength", Lmax="1.95*wavelength",
                        xwidth=0.015, yheight=0.015,
                        restore_neutron=1)

    instrument.settings(ncount=5E6)
    data = instrument.backengine()
    return data
