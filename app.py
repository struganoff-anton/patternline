import streamlit as st
from processor import convert_pdf

st.set_page_config(page_title='PatternLine — линии лекал PDF', page_icon='✂️', layout='centered')
st.title('✂️ PatternLine')
st.write('Утолщение векторных линий лекал без перерисовки и изменения масштаба PDF.')
st.info('Подходит для векторных PDF из Grafis и других CAD-программ. PDF с растровыми линиями не преобразуются в векторные.')
files = st.file_uploader('Загрузите PDF', type=['pdf'], accept_multiple_files=True)
mode_label = st.radio('Способ обработки', ['Установить толщину в мм', 'Умножить исходную толщину'], horizontal=False)
mode = 'fixed' if mode_label.startswith('Установить') else 'multiply'
if mode == 'fixed':
    mm = st.slider('Толщина линии, мм', min_value=0.05, max_value=1.0, value=0.30, step=0.05)
    factor = 2.0
else:
    factor = st.slider('Коэффициент', min_value=1.0, max_value=10.0, value=3.0, step=0.5)
    mm = 0.3
st.caption('Обработка меняет параметры штрихов в PDF, не масштабируя страницу. Текст и растровые изображения не утолщаются.')
if files and st.button('Обработать PDF', type='primary'):
    for f in files:
        try:
            result, stats = convert_pdf(f.getvalue(), mm, mode, factor)
            st.success(f'{f.name}: {stats["pages"]} стр., изменено операторов толщины: {stats["operators_changed"]}.')
            st.download_button('⬇️ Скачать ' + f.name, result, file_name=f.name.rsplit('.', 1)[0] + '_толстые_линии.pdf', mime='application/pdf', key=f.name)
        except Exception as exc:
            st.error(f'{f.name}: {exc}')
st.divider()
st.caption('Открытый проект. Перед массовой печатью проверьте контрольный размер 100 × 100 мм и визуально сравните все типы линий.')
