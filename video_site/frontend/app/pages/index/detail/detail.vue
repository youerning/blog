<template>
	<view class="content">
		<text class="title">{{data.vod_name}}{{current_video.name? " - " + current_video.name : ""}}</text>
		<view class="videocontent">
			<view class="video-js" ref="video" />
		</view>
		<view class="title">播放列表</view>
		<!-- <view class="series">
			<button v-for="video_data in data.vod_links"
				:type="video_data.url == current_video.url ? 'primary' : 'defalut'"
				@click="() => changeUrl(video_data)"
				plain="true">{{video_data.name}}</button>
		</view>
		 -->
		<view class="grid col-5 padding-sm">
			<button v-for="video_data in data.vod_links"
				:type="video_data.url == current_video.url ? 'primary' : 'defalut'"
				@click="() => changeUrl(video_data)"
				plain="true"
				>{{video_data.name}}</button>
		</view>
	</view>
</template>

<script>
	export default {
		data() {
			return {
				current_video: {
					name: "",
					url: ""
				},
				data: {}
			}
		},
		methods: {
			changeUrl(video_data) {
				this.current_video = video_data
				var v = videojs('video')
				v.src([
					{type: "application/x-mpegURL", src: video_data.url},
				])
				v.play()
			}
		},
		mounted() {
			// this.current_video = this.data.vod_urls[0]
			var video = document.createElement('video')  
			this.video = video
			this.video.id = 'video'
			// video.style = 'width: 300px;height: 150px;'  
			this.video.controls = true  
			// var source = document.createElement('source')
			// source.src = this.current_video.url
			// this.video.appendChild(source)  
			this.$refs.video.$el.appendChild(video)  
			videojs('video')
		},
		onLoad: function(option) {
			// console.log("recive vod_id: ", option)
			this.video_id = option.vod_id
			uni.request({
				url: "/api/videos/" + option.vod_id
			})
			.then(res => {
				// console.log(res[1].data.data)
				this.data = res[1].data.data[0]
				// console.log(this.data)
				this.current_video = this.data.vod_links[0]
				this.changeUrl(this.current_video)
				
				// 缓存点击多的video id
				uni.getStorage({
				    key: 'video_ids',
				    success: function (res) {
						console.log("获取缓存数据", res)
						const video_ids = res.data.filter((val) => {
							if (val && val != this.video_id) {
								return true
							}
						})
						
						this.video_ids = [option.vod_id].concat(video_ids)
						console.log("缓存数据: ", this.video_ids)
						uni.setStorage({
						    key: 'video_ids',
						    data: this.video_ids,
						});	
				    }
				})
			})
			.catch(err => {
				console.log(err)
				uni.showToast({
					icon: "none",
					duration: 1500,
					title: "没有找到对应的视频内容"
				})
			})
			
		}
	}
</script>

<style>
	.content {
		padding: 0 30rpx;
	}
	
	.title {
		display: -webkit-box;
		padding: 20rpx 0;
		font-size: 24rpx;
		color: #434343;
	}
	
	.videocontent {
		display: flex;
		height: 400rpx;
		display: -webkit-flex;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-flow:row nowrap;
	}
	
	.videocontent view{
		width: 100%;
		height: 100%;
	}
	.series {
		display: flex;
		justify-content: flex-start;
		flex-flow:row wrap;
		display: -webkit-flex;
	}
	
	.series button {
		width: 180rpx;
	}
</style>
