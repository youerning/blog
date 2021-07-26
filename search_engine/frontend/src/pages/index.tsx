import React from 'react';
import { useState } from 'react';
import { Tag, Row, Col, Input, Typography } from 'antd';
import { MessageOutlined, LikeOutlined, StarOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-layout';
import ProList from '@ant-design/pro-list';
import request from 'umi-request';

const { Paragraph, Text } = Typography;
const { Search } = Input;

const IconText = ({ icon, text }: { icon: any; text: string }) => (
  <span>
    {React.createElement(icon, { style: { marginRight: 8 } })}
    {text}
  </span>
);


const styles = {
  marginBottom: "30px"
}

export default () => {
  const [data, setData] = useState([]);

  const onSearch = value => {  
    console.log(value);

    request
    .post("/api/search", {
      data: {
        query: value.split()
      }
    })
    .then(function(response) {
      setData(response.data)
    })
    .catch(function(error) {
      setData([])
    });
  };


  return (
    <PageContainer
      header={{title: "全文歌词搜索引擎 - 歌词搜索"}}
    >
      <Row>
        <Col span={18} offset={3}>
          <Search placeholder="搜索关键词" allowClear onSearch={onSearch} enterButton size="large" style={styles} />
        </Col>
      </Row>
      <ProList<{ title: string }>
            itemLayout="vertical"
            rowKey="id"
            headerTitle="搜索结果"
            dataSource={data}
            metas={{
              title: {},
              subTitle: {},
              description: {
                render: (_, entity) => {
                  // console.log(entity)
                  return (
                  <>
                    <Tag>{entity.score}</Tag>
                  </>
                )},
              },
              actions: {
                render: () => [
                  <IconText icon={StarOutlined} text="156" key="list-vertical-star-o" />,
                  <IconText icon={LikeOutlined} text="156" key="list-vertical-like-o" />,
                  <IconText icon={MessageOutlined} text="2" key="list-vertical-message" />,
                ],
              },
              content: {
                render: (_, entity) => {
                  return (
                    <div>
                     <Paragraph ellipsis={{ rows: 4, expandable: true, symbol: 'more' }}>
                        {entity.doc.lyric.map((item) => {
                          return item? item: <br/>
                        })}
                      </Paragraph>,
                      
                    </div>
                  );
                },
              },
            }}
          />
    </PageContainer>  
  );
};