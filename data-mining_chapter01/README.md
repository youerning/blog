# 数据挖掘指南之推荐系统读书笔记
## 推荐系统
通过协同过滤的方式推荐相关内容.

### 协同过滤
通过查找一个与你相似的用户, 然后将ta喜欢的内容推荐给你.

怎么查找相似用户呢? 使用距离算法或者相关系数.

### 距离算法
通过将用户习惯或动作量化, 转换为可以计算的向量, 通过距离算法可以计算两个向量之间的距离, 通过相关系数计算公式可以计算相似程度. 而距离相近的用户,我们也认为两者相似.


距离算法: 曼哈顿距离、欧几里得距离、闵科夫斯基距离.     
假设两个向量分别是(x1,x2), (y1,y2)

曼哈顿距离

```math
\mid{x_1 - y_1}\mid + \mid{x_2 - y_2}\mid
``` 

欧几里得距离

```math
\sqrt{(x_1 - y_1)^2 + (x_2 - y_2)^2}
``` 


闵可夫斯基距离  

```math
d(x,y) = (\sum_{k=1}^n{\mid{x_k - y_k}\mid^r})^{1/r}
``` 



相关系数: 皮尔森相关系数、余弦相似度.

皮尔森相关系数
```math
r = \frac{\sum_{i=1}^{n}{x_iy_i} - \frac{\sum_{i=1}^{n}{x_i}\sum_{i=1}^{n}{y_i}}{n}}{\sqrt{\sum_{i=1}^{n}{x_i}^2 - {(\sum_{i=1}^{n}{x_i})^2 \over {n}}}\sqrt{\sum_{i=1}^{n}{x_i}^2 - {(\sum_{i=1}^{n}{x_i})^2 \over {n}}}}
``` 

> 皮尔森相关系数可使用np.corrcoef计算   
> np.corrcoef(x, y)     
> output         
> [[correlation(x, x), correlation(x, y)]    
> [correlation(y, x), correlation(y,y)]] 

余弦相关系数
```math
\cos{(x,y)} = \frac{x \cdot y}{{\mid\mid{x}\mid\mid}\times{\mid\mid{y}\mid\mid}}

\mid\mid{x}\mid\mid = \sqrt{\sum_{i=1}^{n}{x_i^2}}
```
> 其中范数可使用np.linalg.norm计算  
> 点积可使用np.dot计算

### 相似度总结
如果数据存在“分数膨胀”问题，就使用皮尔逊相关系数。

如果数据比较“密集”，变量之间基本都存在公有值，且这些距离数据是非常重要的，那就使用欧几里得或曼哈顿距离。

如果数据是稀疏的，则使用余弦相似度。

### K近邻算法

```
# 计算距离
def manhattan(user1, user2):
    return np.sum(np.abs(df_user[user1] - df_user[user2]))
    
# 计算最近用户
def computeNeartNeighbor(username, users):
    """
    计算与之相邻的距离
    :params username: string
    :params users: pd.DataFrame
    """
    distance_lis = []
    
    for user in users.columns:
        if username != user:
            distance = manhattan(username, user)
            distance_lis.append((distance, user))

    distance_lis.sort()
    return distance_lis
    
# 推荐最近用户喜欢而被推荐用户没有评分的作品
def recommend(username, users):
    """
    为username推荐
    :params username: string
    :params users: pd.DataFrame
    """
    nearest = computeNeartNeighbor(username, users)[0][1]
    
    recommandations = []
    neighborRatings = users[nearest]
    userRatings = users[username]
    
    for index, value in enumerate(userRatings):
        #  如果该用户没有评分但是最相关的用户有评分
        if np.isnan(value) and not np.isnan(neighborRatings.iloc[index]):
            recommandations.append((neighborRatings.index[index], neighborRatings.iloc[index]))

    return sorted(recommandations, key=lambda artistTuple: artistTuple[1], reverse=True)

```


在实际使用过程中, k值一般不会为1，所以可以为每个用户的评分加权.


```
 # 汇总K邻近用户的评分
for i in range(self.k):
  # 计算饼图的每个分片
  weight = nearest[i][1] / totalDistance
  # 获取用户名称
  name = nearest[i][0]
  # 获取用户评分
  neighborRatings = self.data[name]
  # 获得没有评价过的商品
  for artist in neighborRatings:
     if not artist in userRatings:
        if artist not in recommendations:
           recommendations[artist] = (neighborRatings[artist]
                                      * weight)
```


## 总结
选择合适的距离算法或者相似度算法找到相似的用户，然后将相似用户的喜好推荐给被推荐用户.


