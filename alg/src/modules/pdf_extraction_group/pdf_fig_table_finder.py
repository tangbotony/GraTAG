from include.utils.mongo_utils import PdfExtractResult
from collections import defaultdict
"""
input 
oss_id: pdf原始oss路径,该接口只能查询单pdf中的内容
outline_elements:[(type, page ,poly), (xx,xx,xx)]

output
key: outline_elements的index
value: [[type, text, url]] 当type为table时,返回text信息
{0: [['table', '120245PPI%PPI \n \nWind \nPPI同比\n拉动\nPPI同比\n拉动\n煤炭开采\n2.6\n-13.8\n-0.36\n化纤\n0.8\n0.4\n0.00\n油气开采\n0.9\n6.5\n0.06\n橡塑\n2.1\n-2.8\n-0.06\n黑色采选\n0.4\n8.0\n0.03\n非金属矿制品\n4.2\n-8.3\n-0.35\n有色采选\n0.3\n7.2\n0.02\n黑色冶炼\n6.2\n-5.4\n-0.34\n非金属矿采选\n0.3\n-2.1\n-0.01\n有色冶炼\n5.7\n2.7\n0.15\n农副食品\n4.0\n-3.8\n-0.15\n金属制品\n3.4\n-1.7\n-0.06\n食品\n1.5\n-1.0\n-0.02\n通用设备\n3.5\n-0.6\n-0.02\n饮料茶酒\n1.2\n0.3\n0.00\n专用设备\n2.8\n-0.7\n-0.02\n烟草\n1.0\n0.8\n0.01\n汽车\n7.6\n-1.7\n-0.13\n纺织\n1.7\n-0.8\n-0.01\n交运设备\n1.0\n-0.3\n0.00\n服装\n0.9\n0.4\n0.00\n电气机械\n8.2\n-4.0\n-0.33\n皮革制鞋\n0.6\n0.9\n0.01\n计算机通信电子\n11.3\n-2.3\n-0.26\n木材加工\n0.6\n-1.1\n-0.01\n仪器仪表\n0.8\n-1.1\n-0.01\n家具\n0.5\n0.3\n0.00\n其他制造业\n0.1\n0.2\n0.00\n造纸\n1.0\n-4.8\n-0.05\n废弃资源利用\n0.9\n-1.6\n-0.01\n印刷\n0.5\n-1.1\n-0.01\n金属、机械设备修理\n0.2\n1.1\n0.00\n文教体娱用品\n1.0\n4.6\n0.04\n电热供应\n7.3\n-1.7\n-0.13\n石油炼焦\n4.6\n-2.2\n-0.10\n燃气\n1.3\n-1.4\n-0.02\n化工\n6.6\n-5.6\n-0.37\n供水\n0.4\n0.9\n0.00\n医药\n1.9\n-0.6\n-0.01\n工业\n100.0\n-2.4\n/\n行业\n权重\n2024年1-5月\n行业\n权重\n2024年1-5月', 'pdf-extracted-element/65d338c18a5d62a2bfdb78c4640e55ca/d72fcf63-0f48-4644-937f-a65e163467f6.png']], 
 1: [['figure', None, 'pdf-extracted-element/65d338c18a5d62a2bfdb78c4640e55ca/ac4e3d63-56c4-4f80-b8cd-b102988ed198.png']]}
"""
def pdf_fig_table_find(oss_id: str, outline_elements: list):
    pdf_extract_result = defaultdict(list)
    pages = [page for _, page, _ in outline_elements]
    elements = PdfExtractResult.objects(oss_id=oss_id, page__in=pages).all()
    for element in elements:
        pdf_extract_result[element.page].append([element.type, element.poly, element.text, element.url])

    result = dict()
    for index, element in enumerate(outline_elements):
        result[index] = retrieve_nearby_elements(element, pdf_extract_result)
    return result

def retrieve_nearby_elements(element, result):
    retrieve_elements = list()
    type_, page, poly = element
    left, top, right, bottom = poly
    type_ = type_.split('_')[0]
    extract_elements = result.get(page, [])
    for extract_element in extract_elements:
        extract_type, extract_poly, extract_text, extract_url = extract_element
        extract_left, extract_top, extract_right, extract_bottom = extract_poly
        if extract_url and type_ == extract_type and ((extract_bottom < top and extract_bottom + 0.1 >= top) 
         or (extract_top > bottom and extract_top - 0.1 <= bottom)):
            retrieve_elements.append([extract_type, extract_text, extract_url])
    return retrieve_elements

if __name__ == '__main__':
    oss_id = 'oss://public-xinyu/test-env/doc_search/test1/df41fe9403e8ba82a1d3c30587321460.pdf'
    outline_elements = [('table_caption', 8, [0.0537, 0.0858, 0.6197, 0.0974]), ('figure_caption', 13 ,[0.3194, 0.3423, 0.5939, 0.353])]
    pdf_fig_table_find(oss_id, outline_elements)