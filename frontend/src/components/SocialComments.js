import React, { useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Avatar } from './ui/avatar';
import { Card } from './ui/card';
import { Instagram, Facebook, ExternalLink, MessageCircle, Send, UserCircle, X } from 'lucide-react';
import { Badge } from './ui/badge';
import { useIsMobile } from '../hooks/useMediaQuery';
import CommentsLayout from '../layouts/CommentsLayout';
import { cn } from '../lib/utils';

const SUPPORTED_CHANNELS = ['instagram', 'facebook'];

const formatTimestamp = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return date.toLocaleString();
};

const PostPreview = ({ post }) => {
  if (!post) return null;

  const isVideo = post.media_type === 'VIDEO' || post.media_type === 'REEL';

  return (
    <Card className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] overflow-hidden mb-3 shadow-card">
      <div className="flex items-start gap-3 p-4 border-b border-[var(--tg-border-soft)]">
        <Avatar className="w-10 h-10">
          <img
            src={post.profile_pic || `https://ui-avatars.com/api/?name=${post.username || 'IG'}`}
            alt={post.username || 'Post Author'}
          />
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[var(--tg-text-primary)] truncate">
            {post.username || 'Unknown'}
          </p>
          <p className="text-xs text-[var(--tg-text-muted)]">{formatTimestamp(post.timestamp)}</p>
        </div>
        {post.permalink && (
          <Button
            variant="ghost"
            size="icon"
            className="text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
            onClick={() => window.open(post.permalink, '_blank')}
            aria-label="Open post in new tab"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="relative aspect-square bg-[var(--tg-surface-muted)]">
        {isVideo ? (
          <div className="absolute inset-0 flex items-center justify-center text-[var(--tg-text-muted)]">
            <MessageCircle className="h-10 w-10 opacity-50" />
          </div>
        ) : (
          <img src={post.media_url} alt={post.caption || 'Post media'} className="w-full h-full object-cover" />
        )}
      </div>
      {post.caption && (
        <div className="p-4 border-t border-[var(--tg-border-soft)]">
          <p className="text-sm text-[var(--tg-text-secondary)] whitespace-pre-line">{post.caption}</p>
        </div>
      )}
    </Card>
  );
};

const CommentListItem = ({ comment, isActive, onSelect }) => {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full text-left rounded-2xl border border-transparent px-3 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--tg-accent-soft)]',
        isActive
          ? 'bg-gradient-to-r from-purple-600/10 to-pink-600/10 border-purple-500/50'
          : 'hover:bg-[var(--tg-chat-hover)]'
      )}
    >
      <div className="flex items-center gap-2.5">
        <Avatar className="w-10 h-10 shrink-0">
          <img
            src={comment.profile_pic || `https://ui-avatars.com/api/?name=${comment.username}`}
            alt={comment.username}
          />
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-[var(--tg-text-primary)] truncate">
              {comment.username}
            </p>
          </div>
          <p className="mt-0.5 text-[11px] text-[var(--tg-text-secondary)] truncate">
            {comment.text || 'No comment text'}
          </p>
          <p className="text-[10px] text-[var(--tg-text-muted)] mt-0.5 whitespace-nowrap">
            {formatTimestamp(comment.timestamp)}
          </p>
        </div>
      </div>
    </button>
  );
};

const ThreadMessage = ({ message, onReply, onMessage }) => {
  if (!message) {
    return null;
  }

  return (
    <div className="flex items-start gap-3 py-3 border-b border-[var(--tg-border-soft)] last:border-b-0">
      <Avatar className="w-10 h-10">
        <img
          src={message.profile_pic || `https://ui-avatars.com/api/?name=${message.username || 'User'}`}
          alt={message.username || 'User'}
        />
      </Avatar>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-[var(--tg-text-primary)] truncate">
            {message.username || 'Unknown'}
          </p>
          <span className="text-xs text-[var(--tg-text-muted)] whitespace-nowrap">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        <p className="mt-2 text-sm text-[var(--tg-text-primary)] whitespace-pre-line">
          {message.text || 'No comment text provided.'}
        </p>
        <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--tg-text-muted)] mt-2">
          <button
            type="button"
            onClick={() => onReply?.(message.id)}
            className="hover:text-[var(--tg-accent-strong)]"
          >
            Reply
          </button>
          <button
            type="button"
            onClick={() => onMessage?.(message.id)}
            className="hover:text-[var(--tg-accent-strong)]"
          >
            Message
          </button>
        </div>
      </div>
    </div>
  );
};

const SocialComments = ({ selectedPlatform = 'all' }) => {
  const [activeTab, setActiveTab] = useState(selectedPlatform === 'all' ? 'instagram' : selectedPlatform);
  const [comments, setComments] = useState({ instagram: [], facebook: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedThread, setSelectedThread] = useState(null);
  const [replyTarget, setReplyTarget] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [search, setSearch] = useState('');
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const isMobile = useIsMobile();

  const fetchComments = useCallback(async (platform) => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };

      const normalize = (list = []) =>
        list.map((item) => ({
          ...item,
          username: item.username || 'Unknown',
          text: item.text || '',
          post: item.post
            ? {
                ...item.post,
                username: item.post.username || item.username || 'Unknown',
                profile_pic: item.post.profile_pic || item.profile_pic || null
              }
            : null,
          replies: (item.replies || []).map((reply) => ({
            ...reply,
            username: reply.username || 'Unknown',
            text: reply.text || '',
            timestamp: reply.timestamp
          }))
        }));

      if (platform === 'all') {
        const [instagramRes, facebookRes] = await Promise.all([
          axios.get(`${API}/instagram/comments`, { headers }),
          axios.get(`${API}/facebook/comments`, { headers })
        ]);
        setComments({
          instagram: normalize(instagramRes.data),
          facebook: normalize(facebookRes.data)
        });
      } else {
        const response = await axios.get(`${API}/${platform}/comments`, { headers });
        setComments((prev) => ({
          ...prev,
          [platform]: normalize(response.data || [])
        }));
      }
    } catch (err) {
      console.error('Error loading comments:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load comments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Set initial tab based on selectedPlatform
    if (selectedPlatform !== 'all') {
      setActiveTab(selectedPlatform);
    }
  }, [selectedPlatform]);

  useEffect(() => {
    // Fetch comments whenever activeTab changes
    const platformToFetch = activeTab === selectedPlatform ? selectedPlatform : activeTab;
    fetchComments(platformToFetch);
  }, [activeTab, selectedPlatform, fetchComments]);

  useEffect(() => {
    const currentList = comments[activeTab] || [];
    if (currentList.length === 0) {
      setSelectedThread(null);
      return;
    }

    if (!selectedThread || !currentList.some((item) => item.id === selectedThread.id)) {
      setSelectedThread(currentList[0]);
      setReplyTarget(currentList[0]);
    }
  }, [comments, activeTab, selectedThread]);

  useEffect(() => {
    if (!selectedThread) {
      setIsProfileOpen(false);
      return;
    }
    setIsProfileOpen(!isMobile);
  }, [selectedThread, isMobile]);

  const currentComments = useMemo(() => {
    const list = comments[activeTab] || [];
    if (!search.trim()) return list;
    const lower = search.toLowerCase();
    return list.filter(
      (comment) =>
        comment.username?.toLowerCase().includes(lower) ||
        comment.text?.toLowerCase().includes(lower) ||
        comment.post?.caption?.toLowerCase().includes(lower)
    );
  }, [comments, activeTab, search]);

  const threadMessages = useMemo(() => {
    if (!selectedThread) {
      return [];
    }
    const replies = Array.isArray(selectedThread.replies) ? selectedThread.replies : [];
    return [
      {
        ...selectedThread,
        kind: 'root'
      },
      ...replies.map((reply) => ({
        ...reply,
        kind: 'reply',
        profile_pic: reply.profile_pic || selectedThread.profile_pic
      }))
    ];
  }, [selectedThread]);

  const handleSendReply = async () => {
    if (!replyTarget || !replyText.trim()) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      await axios.post(
        `${API}/${activeTab}/comments/${replyTarget.id}/reply`,
        { text: replyText },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      await fetchComments(activeTab);
      setReplyText('');
    } catch (err) {
      console.error('Error sending reply:', err);
    }
  };

  const handleSelectThread = (thread) => {
    setSelectedThread(thread);
    setReplyTarget(thread);
    setReplyText('');
    if (!isMobile) {
      setIsProfileOpen(true);
    }
  };

  const handleReplyToMessage = (messageId) => {
    if (!selectedThread) return;
    if (selectedThread.id === messageId) {
      setReplyTarget(selectedThread);
      return;
    }

    const reply = (selectedThread.replies || []).find((item) => item.id === messageId);
    if (reply) {
      setReplyTarget(reply);
    }
  };

  const toggleProfilePanel = () => {
    setIsProfileOpen((prev) => !prev);
  };

  const renderThread = () => {
    if (loading) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="h-10 w-10 rounded-full border-t-2 border-b-2 border-purple-500 animate-spin" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-gray-400 px-6">
          <p className="text-sm mb-3">{error}</p>
          <Button variant="ghost" onClick={() => fetchComments(activeTab)}>
            Retry
          </Button>
        </div>
      );
    }

    if (!selectedThread) {
      return (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
          Select a comment to view the conversation
        </div>
      );
    }

    const replies = selectedThread.replies || [];
    const postSummary = selectedThread.post;

    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="space-y-3">
          <div className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-2xl p-4 shadow-card">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 flex-1">
                <Avatar className="w-10 h-10">
                  <img
                    src={selectedThread.profile_pic || `https://ui-avatars.com/api/?name=${selectedThread.username}`}
                    alt={selectedThread.username}
                  />
                </Avatar>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[var(--tg-text-primary)] truncate">
                    {selectedThread.username}
                  </p>
                  <p className="text-xs text-[var(--tg-text-muted)] mt-1">
                    {formatTimestamp(selectedThread.timestamp)}
                  </p>
                </div>
              </div>
              {isMobile && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
                  onClick={toggleProfilePanel}
                  aria-label={isProfileOpen ? 'Hide profile' : 'Show profile'}
                >
                  {isProfileOpen ? <X className="h-4 w-4" /> : <UserCircle className="h-4 w-4" />}
                </Button>
              )}
            </div>
            <p className="mt-3 text-sm text-[var(--tg-text-secondary)] whitespace-pre-line">
              {selectedThread.text || 'No comment text provided.'}
            </p>
          </div>

          {postSummary && (
            <div className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-2xl p-4 flex gap-3 items-start shadow-card">
              {postSummary.media_url && (
                <div className="w-16 h-16 rounded-xl bg-[var(--tg-surface-muted)] overflow-hidden flex-shrink-0">
                  <img
                    src={postSummary.media_url}
                    alt={postSummary.caption || 'Post media'}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">Post</p>
                <p className="text-sm font-semibold text-[var(--tg-text-primary)]">
                  {postSummary.username || selectedThread.username}
                </p>
                <p className="text-xs text-[var(--tg-text-muted)]">
                  {formatTimestamp(postSummary.timestamp || selectedThread.timestamp)}
                </p>
                {postSummary.caption && (
                  <p className="text-sm text-[var(--tg-text-secondary)] mt-2 whitespace-pre-line">
                    {postSummary.caption}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {isProfileOpen && isMobile && (
          <div className="mb-3">
            <CommentProfilePanel
              thread={selectedThread}
              totalReplies={replies.length}
              isMobile
              platform={activeTab}
            />
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto space-y-1 pr-1 mt-4">
          {threadMessages.length === 0 ? (
            <div className="text-center text-xs text-[var(--tg-text-muted)] py-8">No comments yet.</div>
          ) : (
            threadMessages.map((message) => (
              <ThreadMessage
                key={message.id || `${message.kind}-${message.timestamp}`}
                message={message}
                onReply={handleReplyToMessage}
                onMessage={handleReplyToMessage}
              />
            ))
          )}
        </div>

        <div className="pt-3 border-t border-[var(--tg-border-soft)] mt-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--tg-text-muted)]">
              Replying to{' '}
              <span className="text-[var(--tg-accent-strong)]">
                {replyTarget?.username || selectedThread.username}
              </span>
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
              onClick={() => {
                setReplyTarget(selectedThread);
                setReplyText('');
              }}
            >
              Reset
            </Button>
          </div>
          <div className="flex gap-2">
            <Input
              value={replyText}
              onChange={(event) => setReplyText(event.target.value)}
              placeholder="Write a reply..."
              className="bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] text-[var(--tg-text-primary)] placeholder:text-[var(--tg-text-muted)]"
            />
            <Button
              onClick={handleSendReply}
              disabled={!replyText.trim()}
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderList = () => (
    <div className="flex flex-col h-full bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-2xl shadow-card">
      <div className="p-3 border-b border-[var(--tg-border-soft)] space-y-2.5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-[var(--tg-text-primary)] flex items-center gap-2">
            {activeTab === 'facebook' ? (
              <Facebook className="h-4 w-4 text-blue-500" />
            ) : (
              <Instagram className="h-4 w-4 text-pink-500" />
            )}
            Recent Comments
          </p>
          <span className="text-xs text-[var(--tg-text-muted)]">{currentComments.length} total</span>
        </div>
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search comments..."
          className="comments-filter-input text-sm"
          aria-label="Search comments"
        />
      </div>
      <ScrollArea className="flex-1">
        <div className="px-2 py-1.5 space-y-1.5">
          {currentComments.length === 0 ? (
            <div className="py-10 text-center text-xs text-[var(--tg-text-muted)]">No comments yet</div>
          ) : (
            currentComments.map((comment) => (
              <CommentListItem
                key={comment.id}
                comment={comment}
                isActive={selectedThread?.id === comment.id}
                onSelect={() => handleSelectThread(comment)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );

  const renderPreview = () => {
    if (!selectedThread) {
      return (
        <div className="h-full min-h-0 rounded-3xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] flex items-center justify-center text-sm text-[var(--tg-text-muted)] text-center px-4">
          Select a comment to view post details
        </div>
      );
    }

    return (
      <div className="h-full min-h-0">
        <CommentProfilePanel
          thread={selectedThread}
          totalReplies={(selectedThread.replies || []).length}
          platform={activeTab}
        />
      </div>
    );
  };

  const commentTabs = useMemo(
    () => [
      { id: 'all', label: 'All messages', disabled: true },
      { id: 'messenger', label: 'Messenger', disabled: true, badge: 'Soon' },
      {
        id: 'instagram',
        label: 'Instagram comments',
        icon: Instagram,
        badge: comments.instagram?.length ?? 0
      },
      { id: 'whatsapp', label: 'WhatsApp', disabled: true, badge: 'Soon' },
      {
        id: 'facebook',
        label: 'Facebook comments',
        icon: Facebook,
        badge: comments.facebook?.length ?? 0
      }
    ],
    [comments]
  );

  const handleTabChange = (tabId) => {
    if (!SUPPORTED_CHANNELS.includes(tabId)) {
      return;
    }
    setActiveTab(tabId);
  };

  const previewColumn = isMobile ? null : renderPreview();

  return (
    <CommentsLayout
      tabs={commentTabs}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      postsColumn={renderList()}
      threadColumn={
        <div className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-3xl p-4 flex flex-col h-full min-h-0 shadow-card">
          {renderThread()}
        </div>
      }
      previewColumn={previewColumn}
    />
  );
};

export default SocialComments;

const CommentProfilePanel = ({ thread, totalReplies, isMobile = false, platform }) => {
  if (!thread) {
    return null;
  }

  const platformLabel = (platform || thread.platform || 'instagram').toLowerCase() === 'facebook'
    ? 'Facebook'
    : 'Instagram';

  const platformBadgeClass =
    platformLabel === 'Facebook'
      ? 'bg-blue-500/15 text-blue-600 border border-blue-500/30'
      : 'bg-pink-500/15 text-pink-500 border border-pink-500/30';

  const containerClasses = isMobile
    ? 'bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-2xl p-4'
    : 'bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] rounded-3xl h-full flex flex-col p-4 overflow-y-auto shadow-card';

  const infoItems = [
    { label: 'Comment ID', value: thread.id },
    { label: 'Posted', value: formatTimestamp(thread.timestamp) },
    { label: 'Replies', value: totalReplies },
  ];

  if (thread.post?.permalink) {
    infoItems.push({
      label: 'Permalink',
      value: thread.post.permalink,
      isLink: true,
    });
  }

  return (
    <div className={containerClasses}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Avatar className="w-12 h-12">
            <img
              src={thread.profile_pic || `https://ui-avatars.com/api/?name=${thread.username}`}
              alt={thread.username}
            />
          </Avatar>
          <div>
            <p className="text-base font-semibold text-[var(--tg-text-primary)]">@{thread.username}</p>
            <div className="flex items-center gap-2 mt-1">
              <Badge className={platformBadgeClass}>{platformLabel}</Badge>
              <span className="text-xs text-[var(--tg-text-muted)]">
                {formatTimestamp(thread.timestamp)}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {thread.post && (
          <div>
            <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide mb-2">
              Associated Post
            </p>
            <PostPreview post={thread.post} />
          </div>
        )}

        <div>
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide mb-1">Comment</p>
          <p className="text-sm text-[var(--tg-text-secondary)] whitespace-pre-line">
            {thread.text || 'No comment text provided.'}
          </p>
        </div>

        <div>
          <p className="text-xs uppercase text-[var(--tg-text-muted)] tracking-wide mb-2">Details</p>
          <div className="space-y-2">
            {infoItems.map((item) => (
              <div key={item.label}>
                <p className="text-[11px] uppercase text-[var(--tg-text-muted)]">{item.label}</p>
                {item.isLink ? (
                  <a
                    href={item.value}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-[var(--tg-accent-strong)] hover:underline break-all"
                  >
                    Open post in new tab
                  </a>
                ) : (
                  <p className="text-sm text-[var(--tg-text-primary)] break-all">{item.value}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
