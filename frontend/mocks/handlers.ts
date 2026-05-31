import { v4 as uuidv4 } from 'uuid'
import { HttpResponse, http } from 'msw'

const encoder = new TextEncoder()

export const handlers = [
  // http.get('http://123.57.48.226:5000/api/qa/search/completion', () => {
  //   return HttpResponse.json({
  //     results: ['推荐：法国头号通缉犯被武装劫狱逃脱', '推荐：法国专家美西方应当正确看待中国崛起促进合作共谋繁荣', '推荐：法国大型木偶剧亮相中国'],
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.get('http://123.57.48.226:5000/api/qa/search/history', () => {
  //   return HttpResponse.json({
  //     results: [
  //       {
  //         id: '1',
  //         query: '历史：法国头号通缉犯被武装劫狱逃脱',
  //       },
  //       {
  //         id: '2',
  //         query: '历史：法国专家美西方应当正确看待中国崛起促进合作共谋繁荣',
  //       },
  //       {
  //         id: '3',
  //         query: '历史：法国大型木偶剧亮相中国',
  //       },
  //     ],
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.delete('http://123.57.48.226:5000/api/qa/search/history', () => {
  //   return HttpResponse.json({
  //     results: 'success',
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.delete('http://123.57.48.226:5000/api/qa/search/history/:id', () => {
  //   return HttpResponse.json({
  //     results: 'success',
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.get('http://123.57.48.226:5000/api/qa/recommend', () => {
  //   return HttpResponse.json({
  //     results: ['法国头号通缉犯被武装劫狱逃脱', '法国专家美西方应当正确看待中国崛起促进合作共谋繁荣', '法国大型木偶剧亮相中国'],
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.get('http://123.57.48.226:5000/api/qa/history', () => {
  //   return HttpResponse.json({
  //     results: [
  //       {
  //         qa_series_id: '1',
  //         is_subscribe: true,
  //         create_date: new Date().getTime(),
  //         title: '你能干什么？你能干什么？你能干什么？',
  //       },
  //       {
  //         qa_series_id: '2',
  //         is_subscribe: false,
  //         create_date: new Date().getTime() - (24 * 60 * 60 * 1000),
  //         title: '你能干什么？你能干什么？你能干什么？',
  //       },
  //       {
  //         qa_series_id: '6',
  //         is_subscribe: false,
  //         create_date: new Date().getTime() - (24 * 60 * 60 * 1000),
  //         title: '你能干什么？你能干什么？你能干什么？',
  //       },
  //       {
  //         qa_series_id: '3',
  //         create_date: new Date().getTime() - (24 * 60 * 60 * 1000 * 3),
  //         is_subscribe: false,
  //         title: '你能干什么？',
  //       },
  //       {
  //         qa_series_id: '4',
  //         create_date: new Date().getTime() - (24 * 60 * 60 * 1000 * 9),
  //         is_subscribe: true,
  //         title: '你能干什么？',
  //       },
  //     ],
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.delete('http://123.57.48.226:5000/api/qa/history', () => {
  //   return HttpResponse.json({
  //     results: 'success',
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.delete('http://123.57.48.226:5000/api/qa/series/:qa_series_id', () => {
  //   return HttpResponse.json({}, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.post('http://123.57.48.226:5000/api/qa/series', () => {
  //   return HttpResponse.json({
  //     results: {
  //       qa_series_id: '1',
  //       qa_pair_collection_id: '1',
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.post('http://123.57.48.226:5000/api/qa/collection', () => {
  //   return HttpResponse.json({
  //     results: {
  //       qa_pair_collection_id: uuidv4(),
  //       qa_pair_id: '1',
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.post('http://123.57.48.226:5000/api/qa/complete/ask', () => {
  //   const res = [
  //     {
  //       type: 'additional_query',
  //       additional_query: {
  //         title: '请选择疫情范围：',
  //         options: ['a', 'b', 'c'],
  //         other_option: '',
  //         selected_option: [],
  //       },
  //       qa_pair_id: uuidv4(),
  //     },
  //     {
  //       type: 'additional_query',
  //       additional_query: {
  //         title: '请选择您感兴趣的新闻报道类型：',
  //         options: ['国际新闻：报道国际上发生的事件和活动', '政治新闻：报道政治事件、决策、领导人访问、会议等方面的报道', '社会新闻：报道社会事件、社会热点、人物故事、民生问题等方面的报道', '这是一条较长，会折行的样式，这是一条较长，会折行的样式，这是一条较长，会折行的样式，这是一条较长，会折行的样式，最多50字'],
  //         other_option: '',
  //         selected_option: [],
  //       },
  //       qa_pair_id: uuidv4(),
  //     },
  //   ]

  //   const radom_res = res[Math.floor(Math.random() * res.length)]

  //   return HttpResponse.json({
  //     results: radom_res,
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.get('http://123.57.48.226:5000/api/qa/series/:id', () => {
  //   return HttpResponse.json({
  //     results: {
  //       title: '为什么',
  //       qa_pair_collection_list: [
  //         {
  //           _id: '1',
  //           qa_series_id: 1,
  //           order: 1,
  //           query: '为什么',
  //           qa_pair_list: ['1', '2', '3'],
  //           latest_qa_pair: {
  //             _id: '3',
  //             version: 0,
  //             qa_pair_collection_id: 1,
  //             qa_series_id: 1,
  //             query: '为什么',
  //             general_answer: '你好\n确实，近期法国发生了一起严重的武装劫狱事件。5月14日，一名绰号为“苍蝇”的囚犯穆罕默德·阿姆拉在法国诺曼底大区厄尔省的Incarville高速公路收费站附近被武装分子劫持，并成功逃脱。这起事件造成了2名狱警死亡，另有3人重伤。[SDF12F]阿姆拉现年30岁，出生于诺曼底大区的鲁昂，他被认为是国际毒品交易网络的关键人物，并且有着长达数十项的犯罪记录，包括严重的盗窃、有组织的盗窃团伙、勒索和武装暴力等。[JKLF12F]',
  //             qa_info: {
  //               site_num: 2,
  //               page_num: 3,
  //               word_num: 120000,
  //               additional_query: {
  //                 options: ['a', 'b', 'c'],
  //                 selected_option: ['a'],
  //                 other_option: 'd',
  //                 title: 'test',
  //               },
  //               search_query: ['keyword1', 'keyword2'],
  //               ref_pages: {
  //                 1: {
  //                   id: '1',
  //                   url: 'https://www.baidu.com',
  //                   site: '百度',
  //                   title: '百度一下1',
  //                   summary: '百度一下，你就知道1',
  //                   content: '百度一下，你就知道1',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 2: {
  //                   id: '2',
  //                   url: 'https://www.baidu.com',
  //                   site: '百度',
  //                   title: '百度一下2',
  //                   summary: '百度一下，你就知道2',
  //                   content: '百度一下，你就知道2',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 3: {
  //                   id: '3',
  //                   url: 'http://google.com',
  //                   site: '谷歌',
  //                   title: 'google',
  //                   summary: 'google',
  //                   content: 'google',
  //                   icon: 'https://google.com/favicon.ico',
  //                 },
  //               },
  //             },
  //             timeline_id: {
  //               is_multi_subject: false, // 是否为多主体展示
  //               events: [
  //                 {
  //                   title: '事故发生与紧急响应', // 大标题
  //                   event_list: [
  //                     {
  //                       start_time: '2024-05-10 13:12:00', // 开始时间（不为空）
  //                       end_time: 'NAN', // 结束时间（可以为空）
  //                       img: 'http://xxxxxxxx',
  //                       event_subject: '江苏南通渣土车', // 事件主体（不为空）
  //                       main_character: '学生', // 主要人物（可以为空）
  //                       location: '南通', // 地点（可以为空）
  //                       event_abstract: '江苏南通渣土车撞载学生大巴，学生被紧急疏散。', // 事件摘要（不为空）
  //                       event_title: '江苏南通渣土车撞载学生大巴', // 事件标题（不为空）
  //                       reference_object:
  //                       {
  //                         idx1:
  //                               { // 多篇参考文章情况
  //                                 url: '', // 引用地址
  //                                 title: '', // 引用文章标题
  //                                 chunk_id: '',
  //                                 content: '',
  //                               },
  //                         idx2:
  //                               { // 多篇参考文章情况
  //                                 url: '', // 引用地址
  //                                 title: '', // 引用文章标题
  //                                 chunk_id: '',
  //                                 content: '',
  //                               },

  //                       },
  //                     },
  //                     {
  //                       start_time: '2024-05-10 13:12:00',
  //                       end_time: 'NAN',
  //                       img: 'http://xxxxxxxx',
  //                       event_subject: '江苏南通渣土车',
  //                       main_character: '学生',
  //                       location: '南通',
  //                       event_abstract: '江苏南通渣土车撞载学生大巴，学生被紧急疏散。',
  //                       event_title: '江苏南通渣土车撞载学生大巴',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: '',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },

  //                       },
  //                     },
  //                   ],
  //                 },
  //                 {
  //                   title: '事故发生与紧急响应',
  //                   event_list: [
  //                     {
  //                       start_time: '2024-05-11 14:18:00',
  //                       end_time: 'NAN',
  //                       img: 'http://xxxxxxxx',
  //                       event_subject: '律师',
  //                       main_character: 'NAN',
  //                       location: '南通',
  //                       event_abstract: '律师：车祸责任划分将较为复杂。',
  //                       event_title: '车祸责任划分复杂',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: '',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },

  //                       },
  //                     },
  //                     {
  //                       start_time: '2024-05-11 20:48:00',
  //                       end_time: 'NAN',
  //                       img: 'http://xxxxxxxx',
  //                       event_subject: '事故中一女孩',
  //                       main_character: '女孩',
  //                       location: '南通',
  //                       event_abstract: '事故中一女孩因抢救无效离世。',
  //                       event_title: '事故中一女孩离世',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: '',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },

  //                       },
  //                     },
  //                   ],
  //                 },

  //               ],
  //             },
  //             recommend_query: ['参考1', '参考2'],
  //             reference: [{
  //               id: 'SDF12F',
  //               news_id: '1',
  //               content: '你好',
  //             },
  //             {
  //               id: 'JKLF12F',
  //               news_id: '2',
  //               content: '你好',
  //             }],
  //           },
  //           is_subscribed: false,
  //           create_time: new Date().getTime(),
  //         },
  //         {
  //           _id: '2',
  //           qa_series_id: 1,
  //           order: 1,
  //           query: '为什么',
  //           qa_pair_list: ['1', '2'],
  //           latest_qa_pair: {
  //             _id: '2',
  //             version: 0,
  //             qa_pair_collection_id: 1,
  //             qa_series_id: 1,
  //             query: '为什么',
  //             general_answer: '你好\n确实，近期法国发生了一起严重的武装劫狱事件。5月14日，一名绰号为“苍蝇”的囚犯穆罕默德·阿姆拉在法国诺曼底大区厄尔省的Incarville高速公路收费站附近被武装分子劫持，并成功逃脱。这起事件造成了2名狱警死亡，另有3人重伤。[SDF12F]阿姆拉现年30岁，出生于诺曼底大区的鲁昂，他被认为是国际毒品交易网络的关键人物，并且有着长达数十项的犯罪记录，包括严重的盗窃、有组织的盗窃团伙、勒索和武装暴力等。[JKLF12F]',
  //             qa_info: {
  //               site_num: 2,
  //               page_num: 3,
  //               word_num: 120000,
  //               additional_query: {
  //                 options: ['a', 'b', 'c'],
  //                 selected_option: ['a'],
  //                 other_option: 'd',
  //                 title: 'test',
  //               },
  //               search_query: ['keyword1', 'keyword2'],
  //               ref_pages: {
  //                 1: {
  //                   id: '1',
  //                   url: 'https://www.baidu.com',
  //                   site: '百度',
  //                   title: '百度一下1',
  //                   summary: '百度一下，你就知道1',
  //                   content: '百度一下，你就知道1',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 2: {
  //                   id: '2',
  //                   url: 'https://www.baidu.com',
  //                   site: '百度',
  //                   title: '百度一下2',
  //                   summary: '百度一下，你就知道2',
  //                   content: '百度一下，你就知道2',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 3: {
  //                   id: '3',
  //                   url: 'http://google.com',
  //                   site: '谷歌',
  //                   title: 'google',
  //                   summary: 'google',
  //                   content: 'google',
  //                   icon: 'https://google.com/favicon.ico',
  //                 },
  //               },
  //             },
  //             recommend_query: ['参考1', '参考2'],
  //             reference: [{
  //               id: 'SDF12F',
  //               news_id: '1',
  //               content: '你好',
  //             },
  //             {
  //               id: 'JKLF12F',
  //               news_id: '2',
  //               content: '你好',
  //             }],
  //             timeline_id: {
  //               is_multi_subject: false, // 是否为多主体展示
  //               events: [
  //                 {
  //                   title: null, // 大标题
  //                   event_list: [
  //                     {
  //                       start_time: '2024-05-10 13:12:00', // 开始时间（不为空）
  //                       end_time: 'NAN', // 结束时间（可以为空）
  //                       img: 'http://xxxxxxxx',
  //                       event_subject: '江苏南通渣土车', // 事件主体（不为空）
  //                       main_character: '学生', // 主要人物（可以为空）
  //                       location: '南通', // 地点（可以为空）
  //                       event_abstract: '江苏南通渣土车撞载学生大巴，学生被紧急疏散。', // 事件摘要（不为空）
  //                       event_title: '江苏南通渣土车撞载学生大巴1', // 事件标题（不为空）
  //                       reference_object: {
  //                         url: '', // 引用地址
  //                         title: '', // 引用文章标题
  //                         chunk_id: '',
  //                         content: '',
  //                       },
  //                     },
  //                     {
  //                       start_time: '2024-05-10 13:12:00',
  //                       end_time: 'NAN',
  //                       img: '',
  //                       event_subject: '江苏南通渣土车',
  //                       main_character: '学生',
  //                       location: '南通',
  //                       event_abstract: '江苏南通渣土车撞载学生大巴，学生被紧急疏散。',
  //                       event_title: '江苏南通渣土车撞载学生大巴2',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: '',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },
  //                       },
  //                     },
  //                   ],
  //                 },
  //               ],
  //             },
  //           },
  //           is_subscribed: false,
  //           create_time: new Date().getTime(),
  //         },
  //         {
  //           _id: '3',
  //           qa_series_id: 1,
  //           order: 1,
  //           query: '为什么',
  //           qa_pair_list: ['1', '2'],
  //           latest_qa_pair: {
  //             _id: '2',
  //             version: 0,
  //             qa_pair_collection_id: 1,
  //             qa_series_id: 1,
  //             query: '为什么',
  //             general_answer: '你好\n确实，近期法国发生了一起严重的武装劫狱事件。5月14日，一名绰号为“苍蝇”的囚犯穆罕默德·阿姆拉在法国诺曼底大区厄尔省的Incarville高速公路收费站附近被武装分子劫持，并成功逃脱。这起事件造成了2名狱警死亡，另有3人重伤。[SDF12F]阿姆拉现年30岁，出生于诺曼底大区的鲁昂，他被认为是国际毒品交易网络的关键人物，并且有着长达数十项的犯罪记录，包括严重的盗窃、有组织的盗窃团伙、勒索和武装暴力等。[JKLF12F]',
  //             qa_info: {
  //               site_num: 2,
  //               page_num: 3,
  //               word_num: 120000,
  //               additional_query: {
  //                 options: ['a', 'b', 'c'],
  //                 selected_option: ['a'],
  //                 other_option: 'd',
  //                 title: 'test',
  //               },
  //               search_query: ['keyword1', 'keyword2'],
  //               ref_pages: {
  //                 1: {
  //                   id: '1',
  //                   url: 'https://www.baidu.com?id=1',
  //                   site: '百度',
  //                   title: '百度一下1',
  //                   summary: '百度一下，你就知道1',
  //                   content: '百度一下，你就知道1',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 2: {
  //                   id: '2',
  //                   url: 'https://www.baidu.com?id=2',
  //                   site: '百度',
  //                   title: '百度一下2',
  //                   summary: '百度一下，你就知道2',
  //                   content: '百度一下，你就知道2',
  //                   icon: 'https://www.baidu.com/favicon.ico',
  //                 },
  //                 3: {
  //                   id: '3',
  //                   url: 'http://google.com',
  //                   site: '谷歌',
  //                   title: 'google',
  //                   summary: 'google',
  //                   content: 'google',
  //                   icon: 'https://google.com/favicon.ico',
  //                 },
  //               },
  //             },
  //             recommend_query: ['参考1', '参考2'],
  //             timeline_id: {
  //               is_multi_subject: true, // 是否为多主体展示
  //               events: [
  //                 {
  //                   title: '台媒', // 大标题
  //                   img: 'http://xxxxxxxx',
  //                   event_list: [
  //                     {
  //                       start_time: '2021-12-15 ', // 开始时间（不为空）
  //                       end_time: 'NAN', // 结束时间（可以为空）
  //                       event_subject: '台媒', // 事件主体（不为空）
  //                       main_character: '王力宏', // 主要人物（可以为空）
  //                       location: 'NAN', // 地点（可以为空）
  //                       event_abstract: '台媒曝王力宏已离婚，传出原因是婆媳不和。[idx1]', // 事件摘要（不为空）
  //                       event_title: '台媒曝王力宏已离婚', // 事件标题（不为空）
  //                       img: 'http://xxxxxxxx',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: 'https://www.baidu.com?id=2',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },

  //                       },
  //                     },
  //                   ],
  //                 },
  //                 {
  //                   title: '王力宏',
  //                   img: 'http://xxxxxxxx',
  //                   event_list: [
  //                     {
  //                       start_time: '2021-12-15',
  //                       end_time: 'NAN',
  //                       event_subject: '王力宏',
  //                       main_character: '王力宏',
  //                       location: 'NAN',
  //                       event_abstract: '王力宏发微博承认已提出离婚申请，[idx1]声称和李靓蕾永远是一家人。',
  //                       event_title: '王力宏承认已提出离婚王力宏承认已提出离婚',
  //                       img: 'http://xxxxxxxx',
  //                       reference_object:
  //                       {
  //                         idx1:
  //                           { // 单篇参考文章情况
  //                             url: 'https://www.baidu.com?id=1',
  //                             title: '',
  //                             chunk_id: '',
  //                             content: '',
  //                           },

  //                       },
  //                     },
  //                   ],
  //                 },
  //               ],
  //             },
  //             reference: [{
  //               id: 'SDF12F',
  //               news_id: '1',
  //               content: '你好',
  //             },
  //             {
  //               id: 'JKLF12F',
  //               news_id: '2',
  //               content: '你好',
  //             }],
  //           },
  //           is_subscribed: false,
  //           create_time: new Date().getTime(),
  //         },
  //       ],
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.get('http://123.57.48.226:5000/api/qa/pair/:id', () => {
  //   return HttpResponse.json({
  //     results: {
  //       _id: '1',
  //       version: 0,
  //       qa_pair_collection_id: 1,
  //       qa_series_id: 1,
  //       query: '为什么',
  //       general_answer: '你好\n确实，近期法国发生了一起严重的武装劫狱事件。5月14日，一名绰号为“苍蝇”的囚犯穆罕默德·阿姆拉在法国诺曼底大区厄尔省的Incarville高速公路收费站附近被武装分子劫持，并成功逃脱。这起事件造成了2名狱警死亡，另有3人重伤。[SDF12F]阿姆拉现年30岁，出生于诺曼底大区的鲁昂，他被认为是国际毒品交易网络的关键人物，并且有着长达数十项的犯罪记录，包括严重的盗窃、有组织的盗窃团伙、勒索和武装暴力等。[JKLF12F]',
  //       qa_info: {
  //         site_num: 2,
  //         page_num: 3,
  //         word_num: 120000,
  //         additional_query: {
  //           options: ['a', 'b', 'c'],
  //           selected_option: ['a'],
  //           other_option: 'd',
  //           title: 'test',
  //         },
  //         search_query: ['keyword1', 'keyword2'],
  //         ref_pages: {
  //           1: {
  //             id: '1',
  //             url: 'https://www.baidu.com',
  //             site: '百度',
  //             title: '百度一下1',
  //             summary: '百度一下，你就知道1',
  //             content: '百度一下，你就知道1',
  //             icon: 'https://www.baidu.com/favicon.ico',
  //           },
  //           2: {
  //             id: '2',
  //             url: 'https://www.baidu.com',
  //             site: '百度',
  //             title: '百度一下2',
  //             summary: '百度一下，你就知道2',
  //             content: '百度一下，你就知道2',
  //             icon: 'https://www.baidu.com/favicon.ico',
  //           },
  //           3: {
  //             id: '3',
  //             url: 'http://google.com',
  //             site: '谷歌',
  //             title: 'google',
  //             summary: 'google',
  //             content: 'google',
  //             icon: 'https://google.com/favicon.ico',
  //           },
  //         },
  //       },
  //       recommend_query: ['参考1', '参考2'],
  //       reference: [{
  //         id: 'SDF12F',
  //         news_id: '1',
  //         content: '你好',
  //       },
  //       {
  //         id: 'JKLF12F',
  //         news_id: '2',
  //         content: '你好',
  //       }],
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  http.post('http://123.57.48.226:5000/api/qa/ask', ({ request }) => {
    const stream = new ReadableStream({
      start(controller) {
        // Encode the string chunks using "TextEncoder".
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: { type: 'state', data: 'analyze', query: '你好', qa_series_id: '1', qa_pair_collection_id: '1', qa_pair_id: '1', version: 1 },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'state',
            data: 'search',
            query: '你好',
            qa_series_id: '1',
            qa_pair_collection_id: '1',
            qa_pair_id: '1',
            version: 1,
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'state',
            data: 'organize',
            query: '你好',
            qa_series_id: '1',
            qa_pair_collection_id: '1',
            qa_pair_id: '1',
            version: 1,
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'state',
          data: 'complete',
          query: '你好',
          qa_series_id: '1',
          qa_pair_collection_id: '1',
          qa_pair_id: '1',
          version: 1,
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'qa_pair_info',
            data: {
              site_num: 2,
              page_num: 3,
              word_num: 120000,
              additional_query: {
                options: ['a', 'b', 'c'],
                selected_option: ['a'],
                other_option: 'd',
                title: 'test',
              },
              search_query: ['keyword1', 'keyword2'],
              ref_pages: {
                1: {
                  id: '1',
                  url: 'https://www.baidu.com',
                  site: '百度',
                  title: '百度一下1',
                  summary: '百度一下，你就知道1',
                  content: '百度一下，你就知道1',
                  icon: 'https://www.baidu.com/favicon.ico',
                },
                2: {
                  id: '2',
                  url: 'https://www.baidu.com',
                  site: '百度',
                  title: '百度一下2',
                  summary: '百度一下，你就知道2',
                  content: '百度一下，你就知道2',
                  icon: 'https://www.baidu.com/favicon.ico',
                },
                3: {
                  id: '3',
                  url: 'http://google.com',
                  site: '谷歌',
                  title: 'google',
                  summary: 'google',
                  content: 'google',
                  icon: 'https://google.com/favicon.ico',
                },
              },
            },
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'text',
          data: '你好\n',
          query: '你好',
          qa_series_id: '1',
          qa_pair_collection_id: '1',
          qa_pair_id: '1',
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'ref_answer',
            data: [
              {
                id: 'SDF12F',
                news_id: '1',
                content: '你好',
              },
              {
                id: 'JKLF12F',
                news_id: '2',
                content: '你好',
              },
            ],
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'text',
          data: '确实，近期法国发生了一起严重的武装劫狱事件。5月14日，一名绰号为“苍蝇”的囚犯穆罕默德·阿姆拉在法国诺曼底大区厄尔省的Incarville高速公路收费站附近被武装分子劫持，并成功逃脱。这起事件造成了2名狱警死亡，另有3人重伤。[SDF12F]',
          query: '你好',
          qa_series_id: '1',
          qa_pair_collection_id: '1',
          qa_pair_id: '1',
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'text',
          data: '阿姆拉现年30岁，出生于诺曼底大区的鲁昂，他被认为是国际毒品交易网络的关键人物，并且有着长达数十项的犯罪记录，包括严重的盗窃、有组织的盗窃团伙、勒索和武装暴力等。[JKLF12F]',
          query: '你好',
          qa_series_id: '1',
          qa_pair_collection_id: '1',
          qa_pair_id: '1',
          },
        })}\n\n`))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          results: {
            type: 'recommendation',
          data: ['recom1', 'recom2', 'recom3'],
          query: '你好',
          qa_series_id: '1',
          qa_pair_collection_id: '1',
          qa_pair_id: '1',
          },
        })}\n\n`))
        controller.enqueue(encoder.encode('data: [DONE]'))
        controller.close()
      },
    })
    return new HttpResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
        'Access-Control-Allow-Credentials': 'true',
      },
    })
  }),
  // http.delete('http://123.57.48.226:5000/api/qa/subscribe', () => {
  //   return HttpResponse.json({
  //     results: {
  //       status: true,
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
  // http.post('http://123.57.48.226:5000/api/qa/subscribe', () => {
  //   return HttpResponse.json({
  //     results: {
  //       status: true,
  //     },
  //   }, {
  //     headers: {
  //       'Access-Control-Allow-Origin': 'http://123.57.48.226:5314',
  //       'Access-Control-Allow-Credentials': 'true',
  //     },
  //   })
  // }),
]
