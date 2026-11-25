from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title='Farmacias del Valle', layout='wide')
C=['#781C42','#AD5475','#D38DA7','#777777','#BDBDBD']
@st.cache_data
def cargar():
    d=pd.read_csv(Path(__file__).parent/'datos.csv')
    d['Mes']=pd.to_datetime(d['Mes'],format='%Y-%m')
    return d

d=cargar()
st.title('Farmacias del Valle | Crecer sin descuidar el inventario')
st.markdown('**Tablero ejecutivo · Comercial, compras y logística**')
st.caption('Decisión: priorizar categorías y productos en el abastecimiento. Importes en unidades monetarias (moneda no especificada).')
years=sorted(d.Mes.dt.year.unique())
year=st.sidebar.selectbox('Año',years,index=len(years)-1)
months=st.sidebar.slider('Intervalo de meses',1,12,(1,12))
cats=st.sidebar.multiselect('Categoría',sorted(d.Categoria.unique()),default=sorted(d.Categoria.unique()))
products=sorted(d.loc[d.Categoria.isin(cats),'Producto_Nombre'].unique())
prods=st.sidebar.multiselect('Producto (vacío = todos)',products)
seasons=st.sidebar.multiselect('Temporada',sorted(d.Temporada.unique()),default=sorted(d.Temporada.unique()))
promo=st.sidebar.selectbox('Promoción',['Todas','Con promoción','Sin promoción'])
base=d[d.Categoria.isin(cats)&d.Temporada.isin(seasons)&d.Mes.dt.month.between(*months)]
if prods: base=base[base.Producto_Nombre.isin(prods)]
if promo!='Todas': base=base[base.Promocion.eq(int(promo=='Con promoción'))]
a=base[base.Mes.dt.year.eq(year)].copy(); b=base[base.Mes.dt.year.eq(year-1)]
if a.empty:
    st.warning('No hay registros para esta selección. Cambia los filtros.'); st.stop()
def metrics(x):
    r=x.Ingreso_Mensual.sum(); u=x.Unidades_Vendidas.sum()
    return [r,u,r/u if u else float('nan')]
st.subheader(f'Desempeño de {year}')
st.caption(f'Comparación con los mismos filtros y meses de {year-1}; N/D si no existe base comparable.')
for col,label,v,p,fmt in zip(st.columns(3),['Ingresos totales','Unidades vendidas','Ingreso por unidad'],metrics(a),metrics(b),['{:,.2f}','{:,.0f}','{:,.2f}']):
    delta=f'{(v/p-1)*100:+.2f}% vs. {year-1}' if pd.notna(p) and p>0 and len(b) else None
    col.metric(label,fmt.format(v),delta); col.caption('Anterior: '+fmt.format(p) if len(b) and pd.notna(p) else 'Anterior: N/D')
def chart(fig, x=None,y=None):
    fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=20,b=10),legend_title_text='',xaxis_title=x,yaxis_title=y)
    st.plotly_chart(fig,use_container_width=True)
trend=pd.concat([a,b]).assign(Mes_num=lambda z:z.Mes.dt.month,Anio=lambda z:z.Mes.dt.year.astype(str)).groupby(['Mes_num','Anio'],as_index=False).Ingreso_Mensual.sum()
cat=a.groupby('Categoria',as_index=False).Ingreso_Mensual.sum().sort_values('Ingreso_Mensual',ascending=False)
lead=cat.iloc[0]; share=lead.Ingreso_Mensual/a.Ingreso_Mensual.sum()*100
left,right=st.columns(2)
with left:
    st.subheader('1. ¿Cómo evolucionan los ingresos?')
    chart(px.line(trend,x='Mes_num',y='Ingreso_Mensual',color='Anio',markers=True,color_discrete_sequence=C),'Mes','Ingresos')
    peak=a.groupby('Mes').Ingreso_Mensual.sum().idxmax(); st.caption(f'Mayor ingreso del periodo: {peak:%Y-%m}.')
with right:
    st.subheader('2. ¿Qué categoría lidera?')
    chart(px.bar(cat,x='Ingreso_Mensual',y='Categoria',orientation='h',color_discrete_sequence=C),'Ingresos','Categoría')
    st.caption(f'{lead.Categoria} lidera con {lead.Ingreso_Mensual:,.2f} unidades monetarias.')
left,right=st.columns(2)
with left:
    st.subheader('3. ¿Dónde se concentran los ingresos?')
    chart(px.pie(cat,names='Categoria',values='Ingreso_Mensual',hole=.55,color_discrete_sequence=C))
    st.caption(f'{lead.Categoria} representa {share:.1f}% del ingreso seleccionado.')
with right:
    st.subheader('4. ¿Cuándo aumenta la demanda?')
    s=a.groupby('Temporada',as_index=False).Unidades_Vendidas.mean().sort_values('Unidades_Vendidas',ascending=False)
    chart(px.bar(s,x='Temporada',y='Unidades_Vendidas',color_discrete_sequence=C),'Temporada','Unidades medias por producto-mes')
    st.caption(f'{s.iloc[0].Temporada}: mayor promedio observado ({s.iloc[0].Unidades_Vendidas:,.0f} unidades).')
st.subheader('5. ¿Qué productos requieren revisar existencias?')
p=a.groupby(['Producto_Nombre','Categoria'],as_index=False)[['Unidades_Vendidas','Stock_Disponible']].mean()
chart(px.scatter(p,x='Unidades_Vendidas',y='Stock_Disponible',color='Categoria',hover_name='Producto_Nombre',color_discrete_sequence=C),'Ventas medias por mes','Stock medio reportado')
st.caption('Revisar productos con ventas altas y stock relativamente bajo. El stock no tiene momento de medición documentado; no constituye evidencia de faltantes.')
st.info(f'Acción sugerida: revisar primero la disponibilidad de {lead.Categoria}, contrastando con tiempos de reposición y existencias actuales.')
with st.expander('Metodología, fuentes y datos filtrados'):
    st.write('Fuente única: CSV Farmacias_Valle_Demanda_1200, proporcionado en clase. Integra dimensiones de ventas, catálogo, promociones e inventario. Sin fuentes independientes, costos, metas ni información por sucursal. No se infiere causalidad ni rentabilidad.')
    st.write('Ingreso por unidad = ingreso total / unidades totales. La variación compara los mismos meses y filtros del año anterior. Los promedios de demanda y stock utilizan registros producto-mes.')
    st.dataframe(a,use_container_width=True)
    st.download_button('Descargar datos filtrados',a.to_csv(index=False).encode('utf-8-sig'),'datos_filtrados.csv','text/csv')
