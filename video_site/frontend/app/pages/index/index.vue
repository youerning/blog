<template>
	<view class="content">
		<uni-search-bar placeholder="搜索" @confirm="search"></uni-search-bar>
		<view>
			<scroll-view scroll-y="true" class="scroll-Y" @scrolltoupper="upper" @scrolltolower="lower"
			@scroll="scroll">
				<block v-for="item in data" >
					<uni-card
						:title="item.vod_name"
						:key="item.vod_id"
						:is-shadow="true"
						:extra="item.vod_addtime"
						:note="item.vod_continu"
						>
						<view class="detail" @click="() => gotoDetail(item.vod_id)">
							<image :src="item.vod_pic" mode="widthFix" class="index-image"></image>
							<text>{{"演员: " + item.vod_actor.slice(0, 30) + "..." + "\n\n"}}  {{item.vod_content}}</text>
						</view>
					</uni-card>
				</block>
			</scroll-view>
		</view>
	</view>
</template>

<script>
	export default {
		data() {
			return {
				video_ids: [],
				data: []
			}
		},
		onLoad() {
			var that = this
			uni.getStorage({
			    key: 'video_ids',
			    success: function (res) {
					this.video_ids = res.data
					console.log("获取缓存数据", this.video_ids)
					
					if (this.video_ids.length >= 1) {
						uni.request({
							url: "/api/videos",
							data: {
								video_ids: this.video_ids
							},
							method:"POST",
							success: (res) => {
								that.data = res.data.data
								// console.log(that.data)
							}
						})
					}
			    },
				fail: function(err) {
					// console.log(err)
					uni.setStorage({
					    key: 'video_ids',
					    data: [],
					    success: function () {
					        console.log('将历史记录重置为空数组');
					    }
					});
				}
			});
		},
		methods: {
			gotoDetail(vod_id) {
				console.log("click ", vod_id)
				uni.navigateTo({url: "/pages/index/detail/detail?vod_id=" + vod_id})
			},
			search(value) {
				// console.log(value)
				uni.request({
					url: '/api/search?q=' + value.value,
				}).then((res) => {
					this.data = res[1].data.data
					console.log(this.data)
					// console.log(res[])
				}).catch((err) => {
					uni.showToast({
					    title: '请求失败',
					    duration: 2000,
						icon: none
					});
				})
			}
		}
	}
</script>

<style>
	/* .content {
		padding:15upx 50upx 0upx 50upx;
	} */ 
	.detail {
		font-size: 30rpx;
		height: 350rpx;
		display: -webkit-flex;
		display: flex;
		align-items: flex-start;
		justify-content: space-around;
		flex-flow: row nowrap;
	}
	
	.detail image {
		width: 270rpx;
	}
	
	.detail text {
		padding-left: 10rpx;
		width: 450rpx;
		display: -webkit-box;
		overflow: hidden;
		text-overflow: ellipsis;
		word-wrap: break-word;
		white-space: normal !important;
		-webkit-line-clamp: 8;
		-webkit-box-orient: vertical;
	}
</style>
