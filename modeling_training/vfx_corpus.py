"""Original synthetic CGI controls + axis/unit curriculum, frozen before training."""
import argparse,hashlib,json,random
from pathlib import Path
from modeling_training.corpus import build_rows,validate_example
from modeling_training.vfx_ops import SYSTEM,validate_operation

def rows(split,count,seed):
    rng=random.Random(seed)
    result=[]
    for i in range(count):
        family=i%(7 if split=='train' else 6)
        if split=='train' and family==5: family=4
        if family==6: family=5
        name=f'{split}_Element_{i:03d}'
        variant=(i//7)%3 if split=='train' else i%3
        heldout=split=='test'
        if family==0:
            value=rng.choice([.125,.25,.375,.5,.625,.75,1.25,1.5])
            op=dict(op='light_power',target=name,watts=value*1000)
            facts={'watts':value*1000}
            prompt=[f'Set area light {name} to {value} kilowatts.',f'The area light named {name} should use {value*1000:g} watts.',f'Change the power of {name}, an area light, to {value} kW.'][variant]
            if heldout: prompt=f'For the existing area light called {name}, dial in an output power of {value} kilowatts; leave everything else alone.'
        elif family==1:
            mm=rng.choice([28,32,40,45,55,65,75,85,95])
            op=dict(op='camera_lens',target=name,millimeters=mm);facts={'millimeters':mm}
            prompt=[f'Set camera {name} focal length to {mm} mm.',f'Use a {mm/10:g} cm focal length on camera {name}.',f'The lens on {name} must have a focal length of {mm} millimetres.'][variant]
            if heldout: prompt=f'Keep the shot framing controls editable: change only the focal length on existing camera {name} to {mm/10:g} centimetres.'
        elif family==2:
            rough=rng.choice([15,25,35,45,55,65,75,85]);metal=rng.choice([0,20,40,60,80,100])
            op=dict(op='surface',target=name,roughness=rough/100,metallic=metal/100);facts={'roughness':rough/100,'metallic':metal/100}
            prompt=[f'Set material roughness of mesh {name} to {rough}% and metallic to {metal}%.',f'Mesh {name}: roughness {rough/100}, metallic {metal/100}.',f'Change the existing surface on {name} to {metal} percent metallic and {rough} percent roughness.'][variant]
            if heldout: prompt=f'On the existing material belonging to {name}, make metallic {metal} percent and roughness {rough} percent, preserving its color.'
        elif family==3:
            threshold=rng.choice([.4,.6,.8,1.2,1.4,1.6,1.8]);strength=rng.choice([15,25,35,45,55,65,75,85])
            op=dict(op='glow',target=name,threshold=threshold,strength=strength/100);facts={'threshold':threshold,'strength':strength/100}
            prompt=[f'Set existing compositor glare node {name} threshold to {threshold} and strength to {strength}%.',f'For glow node {name}, use strength {strength/100} and threshold {threshold}.',f'Change {name}, the existing glare compositor node: threshold {threshold}, strength {strength} percent.'][variant]
            if heldout: prompt=f'The current Glare node is named {name}. Adjust its strength to {strength} percent, with a threshold of {threshold}; retain its other settings.'
        else:
            axis=(i//6)%3; sign=-1 if (i//3)%2 else 1
            cm=rng.choice([1,2,3,4] if family==5 else [3,7,11,13,17,23,27,33]);distance=round(sign*cm/100,4)
            delta=[0,0,0];delta[axis]=distance
            facts={'axis':'XYZ'[axis],'distance':distance,'input_centimeters':sign*cm}
            if family==4:
                op=dict(op='transform',target=name,translation=delta,scale=[1,1,1],rotation_degrees=[0,0,0])
                prompt=[f'Move the whole object {name} {sign*cm} cm along {facts["axis"]}. Preserve rotation, scale and other axes.',f'Translate {name} as a whole by {distance} metres on {facts["axis"]}; no rotation or scaling.',f'Shift object {name} by {sign*cm} centimetres in the {facts["axis"]} direction only.'][variant]
                if heldout: prompt=f'Reposition the entire mesh named {name}: a displacement of {sign*cm} centimetres on its {facts["axis"]} axis. Leave its orientation, size and remaining coordinates intact.'
            else:
                center=[0,0,1.2];radius=[.3,.25,.2]
                facts.update(mode='translate',center=center,radius=radius)
                op=dict(op='deform',target=name,center=center,radius=radius,translation=delta,scale=[1,1,1])
                region='ellipsoid center [0,0,1.2] metres and radii [0.3,0.25,0.2] metres'
                prompt=f'Locally displace vertices of {name} {sign*cm} centimetres along {facts["axis"]}, using {region}. Keep all scale factors at one and leave outside vertices alone.'
                if heldout: prompt=f'Within an {region}, nudge the vertices of {name} by {sign*cm} cm on {facts["axis"]}. The object transform stays fixed, and there is no scaling.'
        row=dict(id=f'{split}-vfx-{i:03d}',split=split,prompt=prompt,operation=op,facts=facts,provenance='Original synthetic instruction and numerical target; no external model outputs',language_family='held-out wording' if heldout else 'authored curriculum')
        validate_row(row);result.append(row)
    return result

def validate_row(row):
    op=row['operation'];facts=row['facts']
    validate_operation(op,[op['target']] if 'target' in op else [])
    if op['op'] in ('light_power','camera_lens','surface','glow'):
        assert {k:v for k,v in op.items() if k not in ('op','target')}==facts
    else:
        validate_example(row)
        if 'input_centimeters' in facts:
            assert abs(facts['distance']-facts['input_centimeters']/100)<1e-10

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    manifest={'system':SYSTEM,'files':{},'scope':'Single existing-element edits: light power, camera lens, surface, glare and modeling operations; no VFX simulation or anatomy generation','split_limitations':'Test has separately authored sentence forms and names, but shares numerical ranges and task families. Small synthetic benchmark.','license_note':'Original synthetic data, with 96 newly generated replay examples from original modeling curriculum. No external assets or teacher outputs.'}
    for split,count,seed in [('train',224,27101),('validation',12,27102),('test',24,27103)]:
        items=rows(split,count,seed)
        if split=='train': items+=build_rows('replay',96,27104)
        path=out/(split+'.jsonl');path.write_text(''.join(json.dumps(r)+'\n' for r in items),encoding='utf-8')
        manifest['files'][split]={'count':len(items),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest['files']))

if __name__=='__main__': main()
