```# Voting Functionality Implementation

## 🗳️ Overview

This document describes the voting functionality implementation in the Polly application. The voting system allows users to create polls, cast votes, and view results in a decentralized manner.

## ✅ Features

### 1. **Poll Creation**
- Users can create polls with a title, description, and multiple options
- Duplicate options are automatically detected and removed
- Polls are associated with a geographical scope

### 2. **Voting**
- Authenticated users can cast votes on active polls
- Each user can vote only once per poll
- Votes are recorded with the user, poll, and selected option
- Vote counts are updated in real-time

### 3. **Results Display**
- Vote results are displayed with visual progress bars
- Percentage calculations show relative popularity of options
- Total vote count is displayed
- User's vote is highlighted in the UI

## 🔧 Implementation Details

### Data Models

#### `Poll` Model
- `title`: The poll question/title
- `description`: Detailed description of the poll
- `created_by`: User who created the poll
- `geographical_scope`: The geographical reach of the poll
- `is_active`: Whether the poll is active for voting
- `created_at`/`updated_at`: Timestamps

#### `PollOption` Model
- `poll`: ForeignKey to the Poll
- `text`: The option text
- `votes`: PositiveIntegerField counting votes (denormalized for performance)
- `created_at`/`updated_at`: Timestamps

#### `Vote` Model
- `poll`: ForeignKey to the Poll
- `option`: ForeignKey to the PollOption
- `user`: ForeignKey to the User who cast the vote
- `created_at`: Timestamp of when the vote was cast

### Views

#### `vote_api` View
- Handles vote submission via HTMX
- Validates user authentication
- Checks for duplicate votes
- Creates the Vote record
- Updates the PollOption.votes count
- Returns updated UI with vote confirmation and results

#### `poll_detail` View
- Displays the poll details
- Shows vote form for users who haven't voted
- Shows vote confirmation and results for users who have voted
- Uses the `vote_combined.html` partial template

### Templates

#### `vote_combined.html`
- Combined template for vote form and results
- Shows radio buttons for option selection
- Shows "Vote" button for each option
- After voting, shows confirmation message
- Displays results with progress bars and vote counts

#### `poll_detail.html`
- Main poll detail page
- Includes the `vote_combined.html` partial template
- Shows poll title, description, and metadata

### Key Fixes

#### Vote Counting
- Fixed issue where vote counts weren't displaying correctly
- Updated templates to use `option.vote_options.count` instead of `option.votes`
- Ensured vote counts are updated in real-time after voting

#### Duplicate Results
- Fixed issue with duplicate results sections
- Created combined template to ensure consistent rendering
- Updated HTMX targets to update the correct elements

#### UI Alignment
- Fixed alignment of radio buttons and vote buttons
- Improved visual hierarchy and spacing
- Ensured consistent styling across all states

## 🧪 Testing

The voting functionality should be tested with the following scenarios:

1. **Poll Creation**
   - Create poll with valid options
   - Create poll with duplicate options
   - Create poll with insufficient options

2. **Voting**
   - Cast vote as authenticated user
   - Attempt to vote as unauthenticated user
   - Attempt to vote twice in the same poll
   - Attempt to vote with invalid option ID

3. **Results Display**
   - Verify vote counts are displayed correctly
   - Verify percentages are calculated correctly
   - Verify user's vote is highlighted
   - Verify results update after voting

4. **Edge Cases**
   - Vote on inactive poll
   - Vote with invalid poll ID
   - Vote with invalid option ID

## 📝 Maintenance Notes

1. **Template Structure**
   - The `vote_combined.html` template contains both the vote form and results
   - This ensures consistent rendering and avoids duplicate results sections
   - When making changes to the voting UI, update this template

2. **Vote Counting**
   - Vote counts are stored in two places:
     - `Vote` model records individual votes
     - `PollOption.votes` field stores denormalized count
   - Both must be updated when a vote is cast

3. **HTMX Integration**
   - The voting functionality uses HTMX for dynamic updates
   - Ensure HTMX attributes (`hx-post`, `hx-target`, `hx-swap`) are correctly set
   - Test HTMX responses after making changes

4. **Authentication**
   - Voting requires authentication
   - Ensure authentication checks are in place in the `vote_api` view
   - Test voting as both authenticated and unauthenticated users
