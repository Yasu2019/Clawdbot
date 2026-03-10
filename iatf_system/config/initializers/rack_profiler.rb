# frozen_string_literal: true

# config/initializers/rack_profiler.rb

if defined?(Rack::MiniProfiler)
  Rack::MiniProfiler.config.authorization_mode = :allow_authorized

  # ユーザーがログインしており、そのロールが 'staff' であればプロファイラを有効にする
  Rack::MiniProfiler.config.user_provider = proc do |env|
    # env から現在のユーザーを取得する方法はアプリケーションによって異なるため適宜調整が必要です。
    # 例えば、Devise を使用している場合は次のようになるかもしれません：
    # current_user = env['warden'].user
    # current_user&.role == 'staff' ? current_user.id : nil

    # または、セッションから直接ユーザーIDを取得し、User モデルを検索することも可能です：
    user_id = env['rack.session']['user_id']
    user = User.find_by(id: user_id)
    user&.role == 'staff' ? user.id : nil
  end
end
