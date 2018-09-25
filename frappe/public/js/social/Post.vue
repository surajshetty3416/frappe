<template>
	<div class="post-card">
		<div class="post-body">
			<div class="pull-right text-muted" v-html="post_time"></div>
			<div class="user-avatar" v-html="user_avatar"></div>
			<div class="user-name">{{ user_name }}</div>
			<div class="content" v-html="post.content"></div>
		</div>
		<post-action :comment_count="comment_count" @comment="toggle_comment()"></post-action>
		<post-comment v-if="show_comment" :comments="this.comments" @post_comment="post_comment"></post-comment>
	</div>
</template>
<script>
import PostComment from './PostComment.vue';
import PostAction from './components/PostAction.vue';
export default {
	props: ['post'],
	components: {
		PostComment,
		PostAction
	},
	data() {
		return {
			user_avatar: frappe.avatar(this.post.owner, 'avatar-medium'),
			post_time: comment_when(this.post.creation),
			user_name: frappe.user_info(this.post.owner).fullname,
			show_comment: false,
			comment_count: 0,
			comments: null
		}
	},
	created() {
		this.get_comment_count()
		frappe.realtime.on('new_post_comment', (post_name) => {
			if(this.post.name === post_name) {
				this.comment_count += 1;
				this.get_comments()
			}
		})
	},
	methods: {
		toggle_comment() {
			this.show_comment = !this.show_comment;
			if(this.show_comment && !this.comments) {
				this.get_comments()
			}
		},
		get_comments() {
			frappe.db.get_list('Post Comment', {
					filters: {
						parent: this.post.name
					},
					fields: ['content', 'name', 'modified'],
					order_by: 'modified desc'
				}).then((comments) => {
					this.comments = comments;
				})
		},
		post_comment(comment) {
			frappe.xcall('frappe.social.doctype.post.post.add_comment', {
				'post_name': this.post.name,
				'comment': comment
			})
		},
		get_comment_count() {
			frappe.db.count('Post Comment', {
				filters: {
					parent: this.post.name
				}
			}).then(count => {
				this.comment_count = count;
			})
		}
	}
}
</script>
<style lang="less">
.post-card {
	margin-bottom: 20px;
	max-width: 500px;
	max-height: 500px;
	min-height: 70px;
	overflow: hidden;
	.post-body {
		padding: 10px 12px;
	}
	cursor: pointer;
	.user-name{
		font-weight: 900;
	}
	.user-avatar {
		float: left;
		margin-right: 10px;
		.avatar {
			width: 48px;
			height: 48px;
		}
		.avatar-frame, .standard-image {
			border-radius: 50%;
		}
	}
	.content {
		margin-left: 58px;
		font-size: 14px;
		img, iframe {
			border-radius: 5px;
			border: none;
		}
	}

}
</style>
