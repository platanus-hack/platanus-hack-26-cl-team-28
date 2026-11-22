import pandas as pd, numpy as np, json
C='data/pruebas/realidad_1000/'
Q=pd.read_csv(C+'cep_cortes.csv')
pol=Q[Q.dim=='politica'].pivot(index='caso',columns='segmento',values=['real_neto','sim_neto'])
gr=pol['real_neto']['Izquierda (1-4)']-pol['real_neto']['Derecha (7-10)']; gs=pol['sim_neto']['Izquierda (1-4)']-pol['sim_neto']['Derecha (7-10)']
print('brecha izq-der real', gr.round(0).to_dict()); print('sim', gs.round(0).to_dict()); print('media abs real %.1f sim %.1f'%(abs(gr).mean(),abs(gs).mean()))
v=Q[Q.dim=='voto'].pivot(index='caso',columns='segmento',values=['real_neto','sim_neto'])
a=v['real_neto']['Votó Jara']-v['real_neto']['Votó Kast']; b=v['sim_neto']['Votó Jara']-v['sim_neto']['Votó Kast']; print('Jara-Kast media abs real %.1f sim %.1f'%(abs(a).mean(),abs(b).mean()))
oc=['cep96-estado-economia','cep96-burocracia','cep96-recorte','cep96-criminalidad','cep96-aporte-economico']
for nombre,g in [('5 con la respuesta en el perfil',Q[Q.caso.isin(oc)]),('5 sin ella',Q[~Q.caso.isin(oc)]),('sin dims politicas, sin respuesta',Q[~Q.caso.isin(oc)&~Q.dim.isin(['politica','voto','gobierno'])]),('solo dims politicas, sin respuesta',Q[~Q.caso.isin(oc)&Q.dim.isin(['politica','voto','gobierno'])]),('solo demograficas, todas',Q[~Q.dim.isin(['politica','voto','gobierno','interes'])])]:
    l=g[abs(g.d_real)>=5]
    print(f"{nombre}: cortes {len(g)} corr {g.d_real.corr(g.d_sim):.2f} misma dir {100*((l.d_real>0)==(l.d_sim>0)).mean():.0f}% de {len(l)} tam real {abs(g.d_real).mean():.1f} sim {abs(g.d_sim).mean():.1f} EAM neto {abs(g.err_neto).mean():.1f}")
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'scripts')
from servidor import metodo; import metodos_banco as mb
casos={c['id']:c for c in json.load(open(C+'casos.json'))}
for c in sorted(set(Q.caso)):
    t=mb.tema_del_caso(casos[c]); d=metodo.datos_de(t)
    print(c, metodo.temas_de(t), sorted(x for x in d if 'inmigr' in x or 'estado' in x or 'gasto' in x or 'marcha' in x or 'apertura' in x))
# grupos por tipo de pregunta
T=pd.read_csv(C+'casos_resultado.csv',index_col=0); K=T[T.grupo=='comparable']
R=[]
for l in open(C+'respuestas.jsonl'):
    f=json.loads(l)
    if 'notas' in f: R.append((f['caso'],f['agente'],100.0*(f['notas'][0]>=5)))
R=pd.DataFrame(R,columns=['caso','agente','a'])
P={}
for l in open(C+'personas.jsonl'):
    f=json.loads(l); g=f['grupos']; x=f['fila']; pos=x.get('posicion_politica')
    P[f['agente']]=dict(politica='No se ubica' if not pos or pos<=0 else 'Izq' if pos<=4 else 'Centro' if pos<=6 else 'Der', edad='18-29' if f['edad']<30 else '30-44' if f['edad']<45 else '45-59' if f['edad']<60 else '60+', religion=g.get('Religión'), educacion=g.get('Nivel educacional'), sexo='M' if f['genero']==0 else 'H', zona=g.get('Zona'), gse='Bajo' if f['quintil']<=1 else 'Medio' if f['quintil']<=3 else 'Alto')
R=R.join(pd.DataFrame(P).T,on='agente')
sets={'valorico (rasgo)':K[K.rasgo=='valorico'].index,'principio':K[K.rasgo=='principio'].index,'medio-ambiente':K[K.area=='medio-ambiente'].index,'consenso real>=80':K[K.real>=80].index,'real 35-50 (sobrestimamos)':K[(K.real>35)&(K.real<=50)].index,'beneficio':K[K.rasgo=='beneficio'].index,'migracion':K[K.area=='migracion'].index}
for n,ids in sets.items():
    g=R[R.caso.isin(ids)]
    print(f"\n{n}: n={len(ids)} real {K.real[ids].mean():.1f} sim {K.sim[ids].mean():.1f}")
    for dim in ['politica','edad','educacion','religion','sexo','gse','zona']:
        m=g.groupby(['caso',dim]).a.mean().groupby(dim).mean()
        print('   ',dim, {k:round(v,0) for k,v in m.items() if k})
